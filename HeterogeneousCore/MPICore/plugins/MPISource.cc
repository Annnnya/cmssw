// C++ headers
#include <memory>
#include <stdexcept>
#include <string>

// MPI headers
#include <mpi.h>

// ROOT headers
#include <TBuffer.h>
#include <TBufferFile.h>
#include <TClass.h>

// CMSSW headers
#include "DataFormats/Provenance/interface/BranchListIndex.h"
#include "DataFormats/Provenance/interface/EventAuxiliary.h"
#include "DataFormats/Provenance/interface/EventSelectionID.h"
#include "DataFormats/Provenance/interface/EventToProcessBlockIndexes.h"
#include "DataFormats/Provenance/interface/LuminosityBlockAuxiliary.h"
#include "DataFormats/Provenance/interface/ProcessHistory.h"
#include "DataFormats/Provenance/interface/ProcessHistoryRegistry.h"
#include "DataFormats/Provenance/interface/RunAuxiliary.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventPrincipal.h"
#include "FWCore/Framework/interface/InputSource.h"
#include "FWCore/Framework/interface/InputSourceDescription.h"
#include "FWCore/Framework/interface/InputSourceMacros.h"
#include "FWCore/Framework/interface/ProductProvenanceRetriever.h"
#include "FWCore/MessageLogger/interface/ErrorObj.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/EmptyGroupDescription.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescriptionFiller.h"
#include "FWCore/Sources/interface/ProducerSourceBase.h"
#include "FWCore/Utilities/interface/EDMException.h"
#include "HeterogeneousCore/MPICore/interface/api.h"
#include "HeterogeneousCore/MPICore/interface/conversion.h"
#include "HeterogeneousCore/MPICore/interface/messages.h"
#include "HeterogeneousCore/MPICore/interface/MPIToken.h"
#include "HeterogeneousCore/MPIServices/interface/MPIService.h"

class MPISource : public edm::ProducerSourceBase {
public:
  explicit MPISource(edm::ParameterSet const& config, edm::InputSourceDescription const& desc);
  ~MPISource() override;
  using InputSource::processHistoryRegistryForUpdate;
  using InputSource::productRegistryUpdate;

  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

private:
  bool setRunAndEventInfo(edm::EventID& id, edm::TimeValue_t& time, edm::EventAuxiliary::ExperimentType&) override;
  void produce(edm::Event&) override;

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

  char port_[MPI_MAX_PORT_NAME];
  MPI_Comm comm_ = MPI_COMM_NULL;
  MPIChannel channel_;
  edm::EDPutTokenT<MPIToken> token_;
  Mode mode_;

  edm::ProcessHistory history_;
};

MPISource::MPISource(edm::ParameterSet const& config, edm::InputSourceDescription const& desc)
    : edm::ProducerSourceBase(config, desc, false),
      token_(produces<MPIToken>()),
      mode_(parseMode(config.getUntrackedParameter<std::string>("mode"))) {
  // make sure MPI is initialised
  MPIService::required();

  // Make sure the EDM MPI types are available.
  EDM_MPI_build_types();

  if (mode_ == kCommWorld) {
    edm::LogAbsolute("MPI") << "MPISource in " << ModeDescription[mode_] << " mode.";

    int world_size, world_rank;
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

    MPI_Group world_group;
    MPI_Comm_group(MPI_COMM_WORLD, &world_group);

    // exchange remote flags with all ranks
    int is_remote = 1;  // mark ourselves as remote
    std::vector<int> all_is_remote(world_size, 0);
    MPI_Allgather(&is_remote, 1, MPI_INT, all_is_remote.data(), 1, MPI_INT, MPI_COMM_WORLD);

    // identify the "local" rank (the controller)
    int local_rank = -1;
    for (int i = 0; i < world_size; ++i) {
      if (all_is_remote[i] == 0) {  // only one local is expected
        local_rank = i;
        break;
      }
    }

    if (local_rank < 0) {
      throw edm::Exception(edm::errors::LogicError)
          << "MPISource could not find any local controller rank in MPI_COMM_WORLD.";
    }

    // create a communicator only between this remote and the local rank
    for (int remote_rank = 0; remote_rank < world_size; ++remote_rank) {
      if (remote_rank == local_rank)
        continue;
      // first rank of this process, then controller rank
      int ranks[2] = {remote_rank, local_rank};
      MPI_Group pair_group;
      MPI_Comm pair_comm;
      MPI_Group_incl(world_group, 2, ranks, &pair_group);
      MPI_Comm_create_group(MPI_COMM_WORLD, pair_group, 0, &pair_comm);

      if (pair_comm != MPI_COMM_NULL) {
        comm_ = pair_comm;
        channel_ = MPIChannel(comm_, 1, world_rank);
      }

      MPI_Group_free(&pair_group);

      edm::LogAbsolute("MPI") << "From remote: Created communicator between remote rank " << remote_rank
                              << " and local rank " << local_rank;
    }
    MPI_Group_free(&world_group);

    // Wait for connection from controller
    MPI_Status status;
    EDM_MPI_Empty_t buffer;
    edm::LogAbsolute("MPI") << "receiving connect from " << world_rank << " from local " << local_rank;
    MPI_Recv(&buffer, 1, EDM_MPI_Empty, 1, EDM_MPI_Connect, comm_, &status);
    edm::LogAbsolute("MPI") << "Connected to controller rank " << status.MPI_SOURCE;

  } else if (mode_ == kIntercommunicator) {
    throw edm::Exception(edm::errors::Configuration) << "Intercommunicator not supported yet.";
  } else {
    throw edm::Exception(edm::errors::Configuration)
        << "Invalid mode \"" << config.getUntrackedParameter<std::string>("mode") << "\"";
  }
}

MPISource::~MPISource() {
  if (mode_ == kIntercommunicator) {
    // Close the intercommunicator.
    MPI_Comm_disconnect(&comm_);

    // Unpublish and close the port.
    MPI_Info port_info;
    MPI_Info_create(&port_info);
    MPI_Info_set(port_info, "ompi_global_scope", "true");
    MPI_Info_set(port_info, "ompi_unique", "true");
    MPI_Unpublish_name("server", port_info, port_);
    MPI_Close_port(port_);
  }
}

//MPISource::ItemTypeInfo MPISource::getNextItemType() {
bool MPISource::setRunAndEventInfo(edm::EventID& event,
                                   edm::TimeValue_t& time,
                                   edm::EventAuxiliary::ExperimentType& type) {
  while (true) {
    MPI_Status status;
    MPI_Message message;
    MPI_Mprobe(MPI_ANY_SOURCE, MPI_ANY_TAG, comm_, &message, &status);
    switch (status.MPI_TAG) {
      // Connect message
      case EDM_MPI_Connect: {
        // receive the message header
        EDM_MPI_Empty_t buffer;
        MPI_Mrecv(&buffer, 1, EDM_MPI_Empty, &message, &status);

        // the Connect message is unexpected here (see above)
        throw cms::Exception("InvalidValue")
            << "The MPISource has received an EDM_MPI_Connect message after the initial connection";
        return false;
      }

      // Disconnect message
      case EDM_MPI_Disconnect: {
        // receive the message header
        EDM_MPI_Empty_t buffer;
        MPI_Mrecv(&buffer, 1, EDM_MPI_Empty, &message, &status);

        // signal the end of the input data
        return false;
      }

      // BeginStream message
      case EDM_MPI_BeginStream: {
        // receive the message header
        EDM_MPI_Empty_t buffer;
        MPI_Mrecv(&buffer, 1, EDM_MPI_Empty, &message, &status);

        // receive the next message
        break;
      }

      // EndStream message
      case EDM_MPI_EndStream: {
        // receive the message header
        EDM_MPI_Empty_t buffer;
        MPI_Mrecv(&buffer, 1, EDM_MPI_Empty, &message, &status);

        // receive the next message
        break;
      }

      // BeginRun message
      case EDM_MPI_BeginRun: {
        // receive the RunAuxiliary
        EDM_MPI_RunAuxiliary_t buffer;
        MPI_Mrecv(&buffer, 1, EDM_MPI_RunAuxiliary, &message, &status);
        // TODO this is currently not used
        edm::RunAuxiliary runAuxiliary;
        edmFromBuffer(buffer, runAuxiliary);

        // receive the ProcessHistory
        history_.clear();
        channel_.receiveProduct(0, history_);
        history_.initializeTransients();
        if (processHistoryRegistryForUpdate().registerProcessHistory(history_)) {
          edm::LogAbsolute("MPI") << "new ProcessHistory registered: " << history_;
        }

        // receive the next message
        break;
      }

      // EndRun message
      case EDM_MPI_EndRun: {
        // receive the RunAuxiliary message
        EDM_MPI_RunAuxiliary_t buffer;
        MPI_Mrecv(&buffer, 1, EDM_MPI_RunAuxiliary, &message, &status);

        // receive the next message
        break;
      }

      // BeginLuminosityBlock message
      case EDM_MPI_BeginLuminosityBlock: {
        // receive the LuminosityBlockAuxiliary
        EDM_MPI_LuminosityBlockAuxiliary_t buffer;
        MPI_Mrecv(&buffer, 1, EDM_MPI_LuminosityBlockAuxiliary, &message, &status);
        // TODO this is currently not used
        edm::LuminosityBlockAuxiliary luminosityBlockAuxiliary;
        edmFromBuffer(buffer, luminosityBlockAuxiliary);

        // receive the next message
        break;
      }

      // EndLuminosityBlock message
      case EDM_MPI_EndLuminosityBlock: {
        // receive the LuminosityBlockAuxiliary
        EDM_MPI_LuminosityBlockAuxiliary_t buffer;
        MPI_Mrecv(&buffer, 1, EDM_MPI_LuminosityBlockAuxiliary, &message, &status);

        // receive the next message
        break;
      }

      // ProcessEvent message
      case EDM_MPI_ProcessEvent: {
        // receive the EventAuxiliary
        edm::EventAuxiliary aux;
        status = channel_.receiveEvent(aux, message);

        // extract the rank of the other process (currently unused)
        int source = status.MPI_SOURCE;
        (void)source;

        // fill the event details
        event = aux.id();
        time = aux.time().value();
        type = aux.experimentType();

        // signal a new event
        return true;
      }

      // unexpected message
      default: {
        throw cms::Exception("InvalidValue")
            << "The MPISource has received an unknown message with tag " << status.MPI_TAG;
        return false;
      }
    }
  }
}

void MPISource::produce(edm::Event& event) {
  // duplicate the MPIChannel and put the copy into the Event
  std::shared_ptr<MPIChannel> channel(new MPIChannel(channel_.duplicate()), [](MPIChannel* ptr) {
    ptr->reset();
    delete ptr;
  });
  event.emplace(token_, std::move(channel));
}

void MPISource::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  descriptions.setComment(
      "This module connects to an \"MPIController\" in a separate CMSSW job, receives all Run, LuminosityBlock and "
      "Event transitions from the remote process and reproduces them in the local one.");

  edm::ParameterSetDescription desc;
  edm::ProducerSourceBase::fillDescription(desc);
  desc.ifValue(
          edm::ParameterDescription<std::string>("mode", "CommWorld", false),
          ModeDescription[kCommWorld] >> edm::EmptyGroupDescription() or
              ModeDescription[kIntercommunicator] >> edm::ParameterDescription<std::string>("name", "server", false))
      ->setComment(
          "Valid modes are CommWorld (use MPI_COMM_WORLD) and Intercommunicator (use an MPI name server to setup an "
          "intercommunicator).");

  descriptions.add("source", desc);
}

#include "FWCore/Framework/interface/InputSourceMacros.h"
DEFINE_FWK_INPUT_SOURCE(MPISource);
