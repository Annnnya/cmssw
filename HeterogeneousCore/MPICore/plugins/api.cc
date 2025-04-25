// C++ standard library headers
#include <array>
#include <cstring>
#include <tuple>
#include <cassert>

// ROOT headers
#include <TBufferFile.h>
#include <TClass.h>

// CMSSW headers
#include "DataFormats/Provenance/interface/EventAuxiliary.h"
#include "DataFormats/Provenance/interface/LuminosityBlockAuxiliary.h"
#include "DataFormats/Provenance/interface/RunAuxiliary.h"

// local headers
#include "api.h"
#include "conversion.h"
#include "messages.h"

namespace {
  // copy the content of an std::string-like object to an N-sized char buffer:
  // if the string is larger than the buffer, copy only the first N bytes;
  // if the string is smaller than the buffer, fill the rest of the buffer with NUL characters.
  template <typename S, size_t N>
  void copy_and_fill(char (&dest)[N], S const& src) {
    if (std::size(src) < N) {
      memset(dest, 0x00, N);
      memcpy(dest, src.data(), std::size(src));
    } else {
      memcpy(dest, src.data(), N);
    }
  }
}  // namespace

// build a new MPIChannel that uses a duplicate of the underlying communicator and the same destination
MPIChannel MPIChannel::duplicate() const {
  MPI_Comm newcomm;
  MPI_Comm_dup(comm_, &newcomm);
  return MPIChannel(newcomm, dest_);
}

// close the underlying communicator and reset the MPIChannel to an invalid state
void MPIChannel::reset() {
  MPI_Comm_disconnect(&comm_);
  dest_ = MPI_UNDEFINED;
}

// fill an edm::RunAuxiliary object from an EDM_MPI_RunAuxiliary buffer
void MPIChannel::edmFromBuffer_(EDM_MPI_RunAuxiliary_t const& buffer, edm::RunAuxiliary& aux) {
  aux = edm::RunAuxiliary(buffer.run, edm::Timestamp(buffer.beginTime), edm::Timestamp(buffer.endTime));
  aux.setProcessHistoryID(
      edm::ProcessHistoryID(std::string(buffer.processHistoryID, std::size(buffer.processHistoryID))));
}

// fill an EDM_MPI_RunAuxiliary buffer from an edm::RunAuxiliary object
void MPIChannel::edmToBuffer_(EDM_MPI_RunAuxiliary_t& buffer, edm::RunAuxiliary const& aux) {
  copy_and_fill(buffer.processHistoryID, aux.processHistoryID().compactForm());
  buffer.beginTime = aux.beginTime().value();
  buffer.endTime = aux.endTime().value();
  buffer.run = aux.id().run();
}

// fill an edm::LuminosityBlockAuxiliary object from an EDM_MPI_LuminosityBlockAuxiliary buffer
void MPIChannel::edmFromBuffer_(EDM_MPI_LuminosityBlockAuxiliary_t const& buffer, edm::LuminosityBlockAuxiliary& aux) {
  aux = edm::LuminosityBlockAuxiliary(
      buffer.run, buffer.lumi, edm::Timestamp(buffer.beginTime), edm::Timestamp(buffer.endTime));
  aux.setProcessHistoryID(
      edm::ProcessHistoryID(std::string(buffer.processHistoryID, std::size(buffer.processHistoryID))));
}

// fill an EDM_MPI_LuminosityBlockAuxiliary buffer from an edm::LuminosityBlockAuxiliary object
void MPIChannel::edmToBuffer_(EDM_MPI_LuminosityBlockAuxiliary_t& buffer, edm::LuminosityBlockAuxiliary const& aux) {
  copy_and_fill(buffer.processHistoryID, aux.processHistoryID().compactForm());
  buffer.beginTime = aux.beginTime().value();
  buffer.endTime = aux.endTime().value();
  buffer.run = aux.id().run();
  buffer.lumi = aux.id().luminosityBlock();
}

// fill an edm::EventAuxiliary object from an EDM_MPI_EventAuxiliary buffer
void MPIChannel::edmFromBuffer_(EDM_MPI_EventAuxiliary_t const& buffer, edm::EventAuxiliary& aux) {
  aux = edm::EventAuxiliary({buffer.run, buffer.lumi, buffer.event},
                            std::string(buffer.processGuid, std::size(buffer.processGuid)),
                            edm::Timestamp(buffer.time),
                            buffer.realData,
                            static_cast<edm::EventAuxiliary::ExperimentType>(buffer.experimentType),
                            buffer.bunchCrossing,
                            buffer.storeNumber,
                            buffer.orbitNumber);
  aux.setProcessHistoryID(
      edm::ProcessHistoryID(std::string(buffer.processHistoryID, std::size(buffer.processHistoryID))));
}

// fill an EDM_MPI_EventAuxiliary buffer from an edm::EventAuxiliary object
void MPIChannel::edmToBuffer_(EDM_MPI_EventAuxiliary_t& buffer, edm::EventAuxiliary const& aux) {
  copy_and_fill(buffer.processHistoryID, aux.processHistoryID().compactForm());
  copy_and_fill(buffer.processGuid, aux.processGUID());
  buffer.time = aux.time().value();
  buffer.realData = aux.isRealData();
  buffer.experimentType = aux.experimentType();
  buffer.bunchCrossing = aux.bunchCrossing();
  buffer.orbitNumber = aux.orbitNumber();
  buffer.storeNumber = aux.storeNumber();
  buffer.run = aux.id().run();
  buffer.lumi = aux.id().luminosityBlock();
  buffer.event = aux.id().event();
}

// fill and send an EDM_MPI_Empty_t buffer
void MPIChannel::sendEmpty_(int tag) {
  EDM_MPI_Empty_t buffer;
  buffer.messageTag = tag;
  MPI_Send(&buffer, 1, EDM_MPI_Empty, dest_, tag, comm_);
}

// fill and send an EDM_MPI_RunAuxiliary_t buffer
void MPIChannel::sendRunAuxiliary_(int tag, edm::RunAuxiliary const& aux) {
  EDM_MPI_RunAuxiliary_t buffer;
  buffer.messageTag = tag;
  edmToBuffer_(buffer, aux);
  MPI_Send(&buffer, 1, EDM_MPI_RunAuxiliary, dest_, tag, comm_);
}

// fill and send an EDM_MPI_RunAuxiliary_t buffer
void MPIChannel::sendLuminosityBlockAuxiliary_(int tag, edm::LuminosityBlockAuxiliary const& aux) {
  EDM_MPI_LuminosityBlockAuxiliary_t buffer;
  buffer.messageTag = tag;
  edmToBuffer_(buffer, aux);
  MPI_Send(&buffer, 1, EDM_MPI_LuminosityBlockAuxiliary, dest_, tag, comm_);
}

// fill and send an EDM_MPI_EventAuxiliary_t buffer
void MPIChannel::sendEventAuxiliary_(edm::EventAuxiliary const& aux) {
  EDM_MPI_EventAuxiliary_t buffer;
  buffer.messageTag = EDM_MPI_ProcessEvent;
  edmToBuffer_(buffer, aux);
  MPI_Send(&buffer, 1, EDM_MPI_EventAuxiliary, dest_, EDM_MPI_ProcessEvent, comm_);
}

// receive an EDM_MPI_EventAuxiliary_t buffer and populate an edm::EventAuxiliary
MPI_Status MPIChannel::receiveEventAuxiliary_(edm::EventAuxiliary& aux, int source, int tag) {
  MPI_Status status;
  EDM_MPI_EventAuxiliary_t buffer;
  MPI_Recv(&buffer, 1, EDM_MPI_EventAuxiliary, source, tag, comm_, &status);
  edmFromBuffer_(buffer, aux);
  return status;
}

// receive an EDM_MPI_EventAuxiliary_t buffer and populate an edm::EventAuxiliary
MPI_Status MPIChannel::receiveEventAuxiliary_(edm::EventAuxiliary& aux, MPI_Message& message) {
  MPI_Status status;
  EDM_MPI_EventAuxiliary_t buffer;
  MPI_Mrecv(&buffer, 1, EDM_MPI_EventAuxiliary, &message, &status);
  edmFromBuffer_(buffer, aux);
  return status;
}

// serialize an object of generic type using its ROOT dictionary, and send the binary blob
void MPIChannel::sendSerializedProduct_(int instance, TClass const* type, void const* product) {
  TBufferFile buffer{TBuffer::kWrite};
  type->Streamer(const_cast<void*>(product), buffer);
  int tag = EDM_MPI_SendSerializedProduct | instance * EDM_MPI_MessageTagWidth_;
  MPI_Send(buffer.Buffer(), buffer.Length(), MPI_BYTE, dest_, tag, comm_);
}

// send simple datatypes directly
void MPIChannel::sendTrivialProduct_(int instance, edm::ObjectWithDict const& product) {
  int tag = EDM_MPI_SendTrivialProduct | instance * EDM_MPI_MessageTagWidth_;
  MPI_Send(product.address(), product.typeOf().size(), MPI_BYTE, dest_, tag, comm_);
}

// receive a binary blob, and deserialize an object of generic type using its ROOT dictionary
void MPIChannel::receiveSerializedProduct_(int instance, TClass const* type, void* product) {
  int tag = EDM_MPI_SendSerializedProduct | instance * EDM_MPI_MessageTagWidth_;
  MPI_Message message;
  MPI_Status status;
  MPI_Mprobe(dest_, tag, comm_, &message, &status);
  int size;
  MPI_Get_count(&status, MPI_BYTE, &size);
  TBufferFile buffer{TBuffer::kRead, size};
  MPI_Mrecv(buffer.Buffer(), size, MPI_BYTE, &message, &status);
  type->Streamer(product, buffer);
}

void MPIChannel::receiveTrivialProduct_(int instance, edm::ObjectWithDict& product) {
  int tag = EDM_MPI_SendTrivialProduct | instance * EDM_MPI_MessageTagWidth_;
  MPI_Message message;
  MPI_Status status;
  MPI_Mprobe(dest_, tag, comm_, &message, &status);
  int size;
  MPI_Get_count(&status, MPI_BYTE, &size);
  assert(static_cast<int>(product.typeOf().size()) == size);
  MPI_Mrecv(product.address(), size, MPI_BYTE, &message, MPI_STATUS_IGNORE);
}

// transfer a wrapped object using its TrivialCopyTraits
void MPIChannel::sendTrivialCopyProduct_(int instance, edm::WrapperBase const* wrapper) {
  int tag = EDM_MPI_SendTrivialCopyProduct | instance * EDM_MPI_MessageTagWidth_;

  // if the wrapped type requires it, send the properties required toinitialise the remote copy
  if (wrapper->hasTrivialCopyProperties()) {
    edm::AnyBuffer buffer = wrapper->trivialCopyParameters();
    MPI_Send(buffer.data(), buffer.size_bytes(), MPI_BYTE, dest_, tag, comm_);
  }

  // transfer the memory regions
  auto regions = wrapper->trivialCopyRegions();
  // TODO send the number of regions ?
  for (size_t i = 0; i < regions.size(); ++i) {
    assert(regions[i].data() != nullptr);
    MPI_Send(regions[i].data(), regions[i].size_bytes(), MPI_BYTE, dest_, tag, comm_);
  }
}

// receive a wrapped object using its TrivialCopyTraits
void MPIChannel::receiveTrivialCopyProduct_(int instance, edm::WrapperBase* wrapper) {
  int tag = EDM_MPI_SendTrivialCopyProduct | instance * EDM_MPI_MessageTagWidth_;

  MPI_Message message;
  MPI_Status status;
  int size;

  // mark the wrapped object as present
  wrapper->markAsPresent();

  // if the wrapped type requires it, send the properties required toinitialise the remote copy
  if (wrapper->hasTrivialCopyProperties()) {
    edm::AnyBuffer buffer = wrapper->trivialCopyParameters();
    MPI_Mprobe(dest_, tag, comm_, &message, &status);
    // check that the message size matches the expected buffer size
    MPI_Get_count(&status, MPI_BYTE, &size);
    assert(static_cast<int>(buffer.size_bytes()) == size);
    // receive the properties
    MPI_Mrecv(buffer.data(), buffer.size_bytes(), MPI_BYTE, &message, &status);
    wrapper->trivialCopyInitialize(buffer);
  }

  // receive the memory regions
  auto regions = wrapper->trivialCopyRegions();
  // TODO receive and validate the number of regions ?
  for (size_t i = 0; i < regions.size(); ++i) {
    assert(regions[i].data() != nullptr);
    MPI_Mprobe(dest_, tag, comm_, &message, &status);
    // check that the message size matches the expected region size
    MPI_Get_count(&status, MPI_BYTE, &size);
    assert(static_cast<int>(regions[i].size_bytes()) == size);
    // receive the data region
    MPI_Mrecv(regions[i].data(), regions[i].size_bytes(), MPI_BYTE, &message, &status);
  }

  // finalize the clone after the trivialCopy, if the type requires it
  wrapper->trivialCopyFinalize();
}

void MPIChannel::putTrivialProduct_(
  int instance,
  edm::WrapperBase const* wrapper,
  std::vector<OffsetSizePair>& putRegions
  ) {
  
  MPI_Aint offset;

  // If necessary, put the init parameters
  if (wrapper->hasTrivialCopyProperties()) {
    edm::AnyBuffer buffer = wrapper->trivialCopyParameters();
    offset = currentOffset_.fetch_add(buffer.size_bytes());
    if (currentOffset_ > windowSize_) {throw std::runtime_error("overflowing window for one sided operation");}
    MPI_Put(buffer.data(), buffer.size_bytes(), MPI_BYTE,
            dest_, offset, buffer.size_bytes(), MPI_BYTE, window_);

    putRegions.push_back({offset, static_cast<int>(buffer.size_bytes())});
  }

  // Put all regions
  auto regions = wrapper->trivialCopyRegions();
  for (const auto& region : regions) {
    assert(region.data() != nullptr);
    offset = currentOffset_.fetch_add(region.size_bytes());
    if (offset > windowSize_) {throw std::runtime_error("overflowing window for one sided operation");}

    MPI_Put(region.data(), region.size_bytes(), MPI_BYTE,
            dest_, offset, region.size_bytes(), MPI_BYTE, window_);

    putRegions.push_back({offset, static_cast<int>(region.size_bytes())});
  }

}

void MPIChannel::serializeAndPutProduct_(
  int instance,
  TClass const* type,
  void const* product,
  std::vector<OffsetSizePair>& putRegions
  ) {
  // Serialize the product into a ROOT buffer
  TBufferFile buffer(TBuffer::kWrite);
  type->Streamer(const_cast<void*>(product), buffer);
  int dataSize = buffer.Length();

  MPI_Aint offset;
  // std::cerr << "serialized put" << std::endl;

  // Put the serialized data into the window at current offset
  offset = currentOffset_.fetch_add(dataSize);
  if (currentOffset_ > windowSize_) {throw std::runtime_error("overflowing window for one sided operation");}

  // std::cerr << "serialized put before" << std::endl;
  MPI_Put(buffer.Buffer(), dataSize, MPI_BYTE,
          dest_, offset, dataSize, MPI_BYTE, window_);
  // std::cerr << "serialized put after" << std::endl;

  // Save offset for metadata
  putRegions.push_back({offset, static_cast<int>(dataSize)});
}


void MPIChannel::sendRegions(int instance, std::vector<OffsetSizePair>& putRegions) {
  int tag = EDM_MPI_FinishedPuttingProduct | instance * EDM_MPI_MessageTagWidth_;
  MPI_Send(
    putRegions.data(),                      // pointer to the first element
    putRegions.size() * sizeof(OffsetSizePair), // total byte size
    MPI_BYTE, dest_, tag, comm_
  );
  // MPI_Win_fence(0, window_);
}

std::vector<OffsetSizePair> MPIChannel::receiveRegions(int instance) {
  int tag = EDM_MPI_FinishedPuttingProduct | instance * EDM_MPI_MessageTagWidth_;
  MPI_Message message;
  MPI_Status status;
  MPI_Mprobe(dest_, tag, comm_, &message, &status);

  int size;
  MPI_Get_count(&status, MPI_BYTE, &size);

  // Now compute how many OffsetSizePair elements that represents
  assert(size % sizeof(OffsetSizePair) == 0);  // Optional sanity check
  int count = size / sizeof(OffsetSizePair);

  std::vector<OffsetSizePair> putRegions(count);
  MPI_Mrecv(putRegions.data(), size, MPI_BYTE, &message, MPI_STATUS_IGNORE);
  // MPI_Win_fence(0, window_);


  return putRegions;
}

void MPIChannel::readTrivialProductFromWindow_(
  int instance,
  edm::WrapperBase* wrapper,
  const std::vector<OffsetSizePair>& putRegions,
  size_t& regionIndex
) {
  wrapper->markAsPresent();

  // Step 1: Copy trivial copy parameters if needed
  if (wrapper->hasTrivialCopyProperties()) {
    edm::AnyBuffer buffer = wrapper->trivialCopyParameters();
    const auto& region = putRegions[regionIndex++];
    assert(static_cast<size_t>(region.size) == buffer.size_bytes());

    std::memcpy(buffer.data(), windowBuffer_.data() + region.offset, buffer.size_bytes());

    wrapper->trivialCopyInitialize(buffer);
  }

  // Step 2: Copy memory regions
  auto regions = wrapper->trivialCopyRegions();
  for (size_t i = 0; i < regions.size(); ++i, ++regionIndex) {
    const auto& region = putRegions[regionIndex];
    assert(regions[i].size_bytes() == static_cast<size_t>(region.size));

    std::memcpy(regions[i].data(), windowBuffer_.data() + region.offset, regions[i].size_bytes());
  }

  wrapper->trivialCopyFinalize();
}



void MPIChannel::readSerializedProductFromWindow_(
  int instance,
  TClass const* type,
  void* product,
  const std::vector<OffsetSizePair>& putRegions,
  size_t& regionIndex
) {
  const auto& region = putRegions[regionIndex++];
  TBufferFile rootBuffer(TBuffer::kRead, region.size, windowBuffer_.data()+region.offset, kFALSE);
  type->Streamer(product, rootBuffer);
}



void MPIChannel::allocateWindow() {
  windowBuffer_.resize(windowSize_);
  MPI_Win_create(windowBuffer_.data(), windowSize_, 1, MPI_INFO_NULL, comm_, &window_);
  MPI_Win_fence(0, window_);
}

void MPIChannel::freeWindow() {
  if (window_ != MPI_WIN_NULL) {
    MPI_Win_fence(0, window_);
    MPI_Win_free(&window_);
    window_ = MPI_WIN_NULL;
  }
}

void MPIChannel::flush() {
  if (dest_ != MPI_UNDEFINED && window_ != MPI_WIN_NULL) {
    MPI_Win_flush(dest_, window_);
  }
}

