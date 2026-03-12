// C++ headers
#include <iostream>
#include <memory>
#include <sstream>

// MPI headers
#include <mpi.h>

// ROOT headers
#include <TBufferFile.h>
#include <TClass.h>

// CMSSW headers
#include "DataFormats/Provenance/interface/BranchKey.h"
#include "DataFormats/Provenance/interface/ProcessHistoryRegistry.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/LuminosityBlock.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Run.h"
#include "FWCore/Framework/interface/one/EDProducer.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/EmptyGroupDescription.h"
#include "FWCore/ParameterSet/interface/ParameterDescriptionNode.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Reflection/interface/ObjectWithDict.h"
#include "FWCore/Reflection/interface/TypeWithDict.h"
#include "FWCore/ServiceRegistry/interface/Service.h"
#include "FWCore/Utilities/interface/Guid.h"
#include "HeterogeneousCore/MPICore/interface/api.h"
#include "HeterogeneousCore/MPICore/interface/messages.h"
#include "HeterogeneousCore/MPICore/interface/MPIToken.h"
#include "HeterogeneousCore/MPIServices/interface/MPIService.h"

/* MPIController class
 *
 * This module runs inside a CMSSW job (the "controller") and connects to an "MPISource" in a separate CMSSW job (the "follower").
 * The follower is informed of all transitions seen by the controller, and can replicate them in its own process.
 *
 * Current limitations:
 *   - support a single "follower"
 *
 * Future work:
 *   - support multiple "followers"
 */

class MPIController : public edm::one::EDProducer<edm::one::WatchRuns, edm::one::WatchLuminosityBlocks> {
public:
  explicit MPIController(edm::ParameterSet const& config);
  ~MPIController() override;

  void beginJob() override;
  void endJob() override;

  void beginRun(edm::Run const& run, edm::EventSetup const& setup) override;
  void endRun(edm::Run const& run, edm::EventSetup const& setup) override;

  void beginLuminosityBlock(edm::LuminosityBlock const& lumi, edm::EventSetup const& setup) override;
  void endLuminosityBlock(edm::LuminosityBlock const& lumi, edm::EventSetup const& setup) override;

  void produce(edm::Event& event, edm::EventSetup const& setup) override;

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

private:
  enum Mode { kInvalid = 0, kCommWorld, kIntercommunicator };
  static constexpr const char* ModeDescription[] = {"Invalid", "CommWorld", "Intercommunicator"};
  Mode parseMode(std::string const& label) {
    if (label == ModeDescription[kCommWorld])
      return kCommWorld;
    else if (label == ModeDescription[kIntercommunicator])
      return kIntercommunicator;
    else
      return kInvalid;
  }

  std::vector<MPI_Comm> comms_;       // one communicator per other rank
  std::vector<MPIChannel> channels_;  // one channel per communicator
  // is it thread safe?
  size_t next_channel_index_ = 0;
  MPI_Comm comm_world_ = MPI_COMM_NULL;
  edm::EDPutTokenT<MPIToken> token_;
  Mode mode_;
};

MPIController::MPIController(edm::ParameterSet const& config)
    : token_(produces<MPIToken>()),
      mode_(parseMode(config.getUntrackedParameter<std::string>("mode")))  //
{
  // make sure that MPI is initialised
  MPIService::required();

  // make sure the EDM MPI types are available
  EDM_MPI_build_types();

  if (mode_ == kCommWorld) {
    edm::LogAbsolute("MPI") << "MPIController in " << ModeDescription[mode_] << " mode.";

    int world_size, world_rank;
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

    comm_world_ = MPI_COMM_WORLD;  // keep for broadcasts, etc.

    MPI_Group world_group;
    MPI_Comm_group(MPI_COMM_WORLD, &world_group);

    // fing out types of other processes in the world
    int is_remote = 0;  // mark ourselves as local
    std::vector<int> all_is_remote(world_size, 0);
    MPI_Allgather(&is_remote, 1, MPI_INT, all_is_remote.data(), 1, MPI_INT, MPI_COMM_WORLD);


    for (int other = 0; other < world_size; ++other) {
      if (other == world_rank)
        continue;
      if (!all_is_remote[other])
        continue;

      // first source rank, then rank of this process (controller)
      int ranks[2] = {other, world_rank};
      MPI_Group pair_group;
      MPI_Comm pair_comm;

      MPI_Group_incl(world_group, 2, ranks, &pair_group);
      MPI_Comm_create_group(MPI_COMM_WORLD, pair_group, 0, &pair_comm);

      if (pair_comm != MPI_COMM_NULL) {
        channels_.emplace_back(pair_comm, 0, world_rank);
        edm::LogAbsolute("MPI") << "From local: Created communicator between ranks " << other << " and " << world_rank;
      } else {
        throw edm::Exception(edm::errors::LogicError) << "Failed to create communicator pair" << "\"";
      }

      MPI_Group_free(&pair_group);
    }

    MPI_Group_free(&world_group);
  } else if (mode_ == kIntercommunicator) {
    edm::LogAbsolute("MPI") << "MPIController in " << ModeDescription[mode_] << " mode.";

    // Look for the port under the name indicated by the parameter "server".
    std::string name = config.getUntrackedParameter<std::string>("name", "server");

    char port[MPI_MAX_PORT_NAME];
    MPI_Lookup_name(name.c_str(), MPI_INFO_NULL, port);

    edm::LogAbsolute("MPI") << "Trying to connect to the MPI server on port " << port;

    MPI_Comm intercomm;
    MPI_Comm_connect(port, MPI_INFO_NULL, 0, MPI_COMM_SELF, &intercomm);

    int remote_size;
    MPI_Comm_remote_size(intercomm, &remote_size);

    if (remote_size != 1) {
      throw edm::Exception(edm::errors::Configuration)
          << "Intercommunicator mode currently supports exactly one remote process, "
          << "but found " << remote_size;
    }

    edm::LogAbsolute("MPI") << "Client connected to " << remote_size << (remote_size == 1 ? " server." : " servers.");

    // Store communicator in the vector
    comms_.push_back(intercomm);

    int world_rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

    // Create the corresponding channel (remote rank is 0 in the intercomm)
    channels_.emplace_back(intercomm, 0, world_rank);
  } else {
    // Invalid mode.
    throw edm::Exception(edm::errors::Configuration)
        << "Invalid mode \"" << config.getUntrackedParameter<std::string>("mode") << "\"";
  }
}

MPIController::~MPIController() {
  // Close the intercommunicator.
  if (mode_ == kIntercommunicator) {
    MPI_Comm_disconnect(&comms_[0]);
  }
}

void MPIController::beginJob() {
  // signal the connection
  for (auto& channel : channels_) {
    channel.sendConnect();
  }

  /* is there a way to access all known process histories ?
  edm::ProcessHistoryRegistry const& registry = * edm::ProcessHistoryRegistry::instance();
  edm::LogAbsolute("MPI") << "ProcessHistoryRegistry:";
  for (auto const& keyval: registry) {
    edm::LogAbsolute("MPI") << keyval.first << ": " << keyval.second;
  }
  */
}

void MPIController::endJob() {
  // signal the disconnection
  for (auto& channel : channels_) {
    channel.sendDisconnect();
  }
}

void MPIController::beginRun(edm::Run const& run, edm::EventSetup const& setup) {
  // signal a new run, and transmit the RunAuxiliary
  /* FIXME
   * Ideally the ProcessHistoryID stored in the run.runAuxiliary() should be the correct one, and
   * we could simply do

  channel_.sendBeginRun(run.runAuxiliary());

   * Instead, it looks like the ProcessHistoryID stored in the run.runAuxiliary() is that of the
   * _parent_ process.
   * So, we make a copy of the RunAuxiliary, set the ProcessHistoryID to the correct value, and
   * transmit the modified RunAuxiliary.
   */
  auto aux = run.runAuxiliary();
  aux.setProcessHistoryID(run.processHistory().id());
  for (auto& channel : channels_) {
    channel.sendBeginRun(aux);

    // transmit the ProcessHistory
    channel.sendProduct(0, run.processHistory());
  }
}

void MPIController::endRun(edm::Run const& run, edm::EventSetup const& setup) {
  // signal the end of run
  /* FIXME
   * Ideally the ProcessHistoryID stored in the run.runAuxiliary() should be the correct one, and
   * we could simply do

  channel_.sendEndRun(run.runAuxiliary());

   * Instead, it looks like the ProcessHistoryID stored in the run.runAuxiliary() is that of the
   * _parent_ process.
   * So, we make a copy of the RunAuxiliary, set the ProcessHistoryID to the correct value, and
   * transmit the modified RunAuxiliary.
   */
  auto aux = run.runAuxiliary();
  aux.setProcessHistoryID(run.processHistory().id());
  for (auto& channel : channels_) {
    channel.sendEndRun(aux);
  }
}

void MPIController::beginLuminosityBlock(edm::LuminosityBlock const& lumi, edm::EventSetup const& setup) {
  // signal a new luminosity block, and transmit the LuminosityBlockAuxiliary
  /* FIXME
   * Ideally the ProcessHistoryID stored in the lumi.luminosityBlockAuxiliary() should be the
   * correct one, and we could simply do

  channel_.sendBeginLuminosityBlock(lumi.luminosityBlockAuxiliary());

   * Instead, it looks like the ProcessHistoryID stored in the lumi.luminosityBlockAuxiliary() is
   * that of the _parent_ process.
   * So, we make a copy of the LuminosityBlockAuxiliary, set the ProcessHistoryID to the correct
   * value, and transmit the modified LuminosityBlockAuxiliary.
   */
  auto aux = lumi.luminosityBlockAuxiliary();
  aux.setProcessHistoryID(lumi.processHistory().id());
  for (auto& channel : channels_) {
    channel.sendBeginLuminosityBlock(aux);
  }
}

void MPIController::endLuminosityBlock(edm::LuminosityBlock const& lumi, edm::EventSetup const& setup) {
  // signal the end of luminosity block
  /* FIXME
   * Ideally the ProcessHistoryID stored in the lumi.luminosityBlockAuxiliary() should be the
   * correct one, and we could simply do

  channel_.sendEndLuminosityBlock(lumi.luminosityBlockAuxiliary());

   * Instead, it looks like the ProcessHistoryID stored in the lumi.luminosityBlockAuxiliary() is
   * that of the _parent_ process.
   * So, we make a copy of the LuminosityBlockAuxiliary, set the ProcessHistoryID to the correct
   * value, and transmit the modified LuminosityBlockAuxiliary.
   */
  auto aux = lumi.luminosityBlockAuxiliary();
  aux.setProcessHistoryID(lumi.processHistory().id());
  for (auto& channel : channels_) {
    channel.sendEndLuminosityBlock(aux);
  }
}

void MPIController::produce(edm::Event& event, edm::EventSetup const& setup) {
  {
    edm::LogInfo log("MPI");
    log << "processing run " << event.run() << ", lumi " << event.luminosityBlock() << ", event " << event.id().event()
        << "\nprocess history:    " << event.processHistory() << "\nprocess history id: " << event.processHistory().id()
        << "\nprocess history id: " << event.eventAuxiliary().processHistoryID() << " (from eventAuxiliary)"
        << "\nisRealData " << event.eventAuxiliary().isRealData() << "\nexperimentType "
        << event.eventAuxiliary().experimentType() << "\nbunchCrossing " << event.eventAuxiliary().bunchCrossing()
        << "\norbitNumber " << event.eventAuxiliary().orbitNumber() << "\nstoreNumber "
        << event.eventAuxiliary().storeNumber() << "\nprocessHistoryID " << event.eventAuxiliary().processHistoryID()
        << "\nprocessGUID " << edm::Guid(event.eventAuxiliary().processGUID(), true).toString();
  }

  // pick communicator in round-robin fashion
  if (channels_.empty()) {
    throw edm::Exception(edm::errors::LogicError) << "MPIController: no available channels to send event data!";
  }

  MPIChannel& selected_channel = channels_[next_channel_index_];
  next_channel_index_ = (next_channel_index_ + 1) % channels_.size();

  edm::LogAbsolute("MPI") << "Event " << event.id().event() << " sent through channel index " << next_channel_index_;

  // signal a new event via this channel
  selected_channel.sendEvent(event.eventAuxiliary());

  // duplicate the selected MPIChannel and store in the event
  std::shared_ptr<MPIChannel> link(new MPIChannel(selected_channel.duplicate()), [](MPIChannel* ptr) {
    ptr->reset();
    delete ptr;
  });
  event.emplace(token_, std::move(link));
}

void MPIController::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  descriptions.setComment(
      "This module connects to an \"MPISource\" in a separate CMSSW job, and transmits all Run, LuminosityBlock and "
      "Event transitions from the current process to the remote one.");

  edm::ParameterSetDescription desc;
  desc.ifValue(
          edm::ParameterDescription<std::string>("mode", "CommWorld", false),
          ModeDescription[kCommWorld] >> edm::EmptyGroupDescription() or
              ModeDescription[kIntercommunicator] >> edm::ParameterDescription<std::string>("name", "server", false))
      ->setComment(
          "Valid modes are CommWorld (use MPI_COMM_WORLD) and Intercommunicator (use an MPI name server to setup an "
          "intercommunicator).");

  descriptions.addWithDefaultLabel(desc);
}

DEFINE_FWK_MODULE(MPIController);
