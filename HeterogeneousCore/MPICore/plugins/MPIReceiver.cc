// C++ include files
#include <utility>

// CMSSW include files
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/WrapperBaseOrphanHandle.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Concurrency/interface/Async.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/Exception.h"
#include "HeterogeneousCore/MPICore/interface/MPIToken.h"

#include "FWCore/Concurrency/interface/Async.h"
#include "FWCore/Concurrency/interface/chain_first.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/ServiceRegistry/interface/Service.h"
#include "FWCore/ServiceRegistry/interface/ServiceMaker.h"
#include "FWCore/Utilities/interface/Exception.h"

#include <condition_variable>
#include <mutex>
#include <cassert>

// local include files
#include "api.h"
#include <TBufferFile.h>
#include <TClass.h>

class MPIReceiver : public edm::stream::EDProducer<edm::ExternalWork> {
public:
  MPIReceiver(edm::ParameterSet const& config)
      : upstream_(consumes<MPIToken>(config.getParameter<edm::InputTag>("upstream"))),
        token_(produces<MPIToken>()),
        instance_(config.getParameter<int32_t>("instance"))  //
  {
    // instance 0 is reserved for the MPIController / MPISource pair
    // instance values greater than 255 may not fit in the MPI tag
    if (instance_ < 1 or instance_ > 255) {
      throw cms::Exception("InvalidValue")
          << "Invalid MPIReceiver instance value, please use a value between 1 and 255";
    }

    auto const& products = config.getParameter<std::vector<edm::ParameterSet>>("products");
    products_.reserve(products.size());
    for (auto const& product : products) {
      auto const& type = product.getParameter<std::string>("type");
      auto const& label = product.getParameter<std::string>("label");
      Entry entry;
      entry.type = edm::TypeWithDict::byName(type);
      entry.wrappedType = edm::TypeWithDict::byName("edm::Wrapper<" + type + ">");
      entry.token = produces(edm::TypeID{entry.type.typeInfo()}, label);

      edm::LogVerbatim("MPIReceiver") << "receive type \"" << entry.type.name() << "\" for label \"" << label
                                      << "\" over MPI channel instance " << this->instance_;

      products_.emplace_back(std::move(entry));
    }
  }

  void acquire(edm::Event const& event, edm::EventSetup const&, edm::WaitingTaskWithArenaHolder holder) final {
    MPIToken token = event.get(upstream_);

    //also try unique or optional
    received_meta_ = std::make_shared<ProductMetadataBuilder>();

    edm::Service<edm::Async> as;
    as->runAsync(
        std::move(holder),
        [this, token]() mutable {
          token.channel()->receiveMetadata(instance_, received_meta_);
          assert((received_meta_->productCount() == products_.size()) &&
                "Receiver number of products is different than expected");
        },
        []() { return "Calling MPIReceiver::acquire()"; });
  }

  void produce(edm::Event& event, edm::EventSetup const&) final {
    // read the MPIToken used to establish the communication channel
    MPIToken token = event.get(upstream_);
    
    std::vector<std::unique_ptr<edm::WrapperBase>> wrappers_;

    size_t full_buffer_size = 0;
    size_t buffer_offset_ = 0;
    size_t index = 0;

    std::vector<MPI_Request> requests;

    if (received_meta_->hasSerialized()) {
      requests.emplace_back();
      serialized_buffer =
          token.channel()->postReceiveSerializedBuffer(instance_, received_meta_->serializedBufLen(), requests.back());
    }

    for (auto const& entry : products_) {
      std::unique_ptr<edm::WrapperBase> wrapper(
          reinterpret_cast<edm::WrapperBase*>(entry.wrappedType.getClass()->New()));

      auto product_meta = received_meta_->getNext();

      if (product_meta.kind == ProductMetadata::Kind::TrivialCopy) {
        assert(wrapper->hasTrivialCopyTraits() && "mismatch between expected and factual metadata type");
        wrapper->markAsPresent();
        edm::AnyBuffer buffer = wrapper->trivialCopyParameters();  // constructs buffer with typeid
        assert(buffer.size_bytes() == product_meta.sizeMeta);
        // TDL: can we add func to AnyBuffer to replace pointer to the data?
        std::memcpy(buffer.data(), product_meta.trivialCopyOffset, product_meta.sizeMeta);
        wrapper->trivialCopyInitialize(buffer);
        token.channel()->receiveInitializedTrivialCopy(instance_, wrapper.get(), requests);
      }

      wrappers_.push_back(std::move(wrapper));
    }

    token.channel()->sendNotify(instance_);
    for (MPI_Request& req : requests) {
      MPI_Wait(&req, MPI_STATUS_IGNORE);
    }

    received_meta_->resetIterator();

    for (auto const& entry : products_) {
      std::unique_ptr<edm::WrapperBase> wrapper = std::move(wrappers_[index]);
      auto product_meta = received_meta_->getNext();

      if (product_meta.kind == ProductMetadata::Kind::Missing) {
        edm::LogWarning("MPIReceiver") << "Product " << entry.type.name() << " was not received.";
        index++;
        continue;  // Skip products that weren't sent
      }

      else if (product_meta.kind == ProductMetadata::Kind::Serialized) {
        full_buffer_size = serialized_buffer->BufferSize();
        auto productBuffer = TBufferFile(TBuffer::kRead, product_meta.sizeMeta);
        productBuffer.SetBuffer(
            serialized_buffer->Buffer() + buffer_offset_, product_meta.sizeMeta, kFALSE /* adopt = false */);
        buffer_offset_ += product_meta.sizeMeta;
        entry.wrappedType.getClass()->Streamer(wrapper.get(), productBuffer);
      }

      else if (product_meta.kind == ProductMetadata::Kind::TrivialCopy) {
        wrapper->trivialCopyFinalize();
      }
      // put the data into the Event
      event.put(entry.token, std::move(wrapper));
      index++;
    }

    assert(buffer_offset_ == full_buffer_size && "serialized data buffer is not equal to the expected length");

    // write a shallow copy of the channel to the output, so other modules can consume it
    // to indicate that they should run after this
    event.emplace(token_, token);
  }

private:
  struct Entry {
    edm::TypeWithDict type;
    edm::TypeWithDict wrappedType;
    edm::EDPutToken token;
  };

  // TODO consider if upstream_ should be a vector instead of a single token ?
  edm::EDGetTokenT<MPIToken> const upstream_;  // MPIToken used to establish the communication channel
  edm::EDPutTokenT<MPIToken> const token_;  // copy of the MPIToken that may be used to implement an ordering relation
  std::vector<Entry> products_;             // data to be read over the channel and put into the Event
  int32_t const instance_;                  // instance used to identify the source-destination pair

  std::shared_ptr<ProductMetadataBuilder> received_meta_;
  std::unique_ptr<TBufferFile> serialized_buffer;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(MPIReceiver);