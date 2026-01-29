// C++ standard library headers
#include <cstring>
#include <iostream>
#include <sstream>

// CMSSW headers
#include "HeterogeneousCore/MPICore/interface/metadata.h"

ProductMetadataBuilder::ProductMetadataBuilder() : buffer_(nullptr), capacity_(0), size_(0), readOffset_(0) {
  // reserve at least 13 bytes for header
  reserve(maxMetadataSize_);
  size_ = headerSize_;
}

ProductMetadataBuilder::ProductMetadataBuilder(int16_t productCount)
    : buffer_(nullptr), capacity_(0), size_(0), readOffset_(0) {
  // we need 1 byte for type, 8 bytes for size, and at least 8 bytes for MemoryCopyTraits Properties buffer
  // on average 24 bytes per product should be enough, but metadata will adapt if the actual contents is larger
  reserve(productCount * 24 + headerSize_);
  header_.productCount = static_cast<int16_t>(productCount);
  size_ = headerSize_;
}

ProductMetadataBuilder::~ProductMetadataBuilder() { std::free(buffer_); }

// Move costructors

ProductMetadataBuilder::ProductMetadataBuilder(ProductMetadataBuilder&& other) noexcept
    : buffer_(other.buffer_),
      capacity_(other.capacity_),
      size_(other.size_),
      readOffset_(other.readOffset_),
      header_(other.header_) {
  other.buffer_ = nullptr;
  other.capacity_ = 0;
  other.size_ = 0;
  other.readOffset_ = 0;
  other.header_ = MetadataHeader{};
}

ProductMetadataBuilder& ProductMetadataBuilder::operator=(ProductMetadataBuilder&& other) noexcept {
  if (this != &other) {
    std::free(buffer_);

    buffer_ = other.buffer_;
    capacity_ = other.capacity_;
    size_ = other.size_;
    readOffset_ = other.readOffset_;
    header_ = other.header_;

    other.buffer_ = nullptr;
    other.capacity_ = 0;
    other.size_ = 0;
    other.readOffset_ = 0;
    other.header_ = MetadataHeader{};
  }
  return *this;
}

// Copy constructors

ProductMetadataBuilder::ProductMetadataBuilder(const ProductMetadataBuilder& other)
    : buffer_(nullptr),
      capacity_(other.capacity_),
      size_(other.size_),
      readOffset_(other.readOffset_),
      header_(other.header_) {
  if (capacity_ > 0) {
    buffer_ = static_cast<uint8_t*>(std::malloc(capacity_));
    if (!buffer_)
      throw std::bad_alloc();
    std::memcpy(buffer_, other.buffer_, size_);
  }
}

ProductMetadataBuilder& ProductMetadataBuilder::operator=(const ProductMetadataBuilder& other) {
  if (this != &other) {
    uint8_t* newBuffer = nullptr;

    if (other.capacity_ > 0) {
      newBuffer = static_cast<uint8_t*>(std::malloc(other.capacity_));
      if (!newBuffer)
        throw std::bad_alloc();
      std::memcpy(newBuffer, other.buffer_, other.size_);
    }

    std::free(buffer_);

    buffer_ = newBuffer;
    capacity_ = other.capacity_;
    size_ = other.size_;
    readOffset_ = other.readOffset_;
    header_ = other.header_;
  }
  return *this;
}

void ProductMetadataBuilder::reserve(size_t bytes) {
  if (capacity_ >= bytes)
    return;
  resizeBuffer(bytes);
}

void ProductMetadataBuilder::setHeader() {
  assert(size_ >= headerSize_ && "Buffer must reserve space for header");
  std::memcpy(buffer_, &header_, sizeof(header_));
}

void ProductMetadataBuilder::addMissing() {
  header_.productFlags |= HasMissing;
  append<uint8_t>(static_cast<uint8_t>(ProductMetadata::Kind::Missing));
}

void ProductMetadataBuilder::addSerialized(uint64_t size) {
  header_.productFlags |= HasSerialized;
  append<uint8_t>(static_cast<uint8_t>(ProductMetadata::Kind::Serialized));
  append<uint64_t>(size);
  header_.serializedBufferSize += static_cast<int32_t>(size);
}

void ProductMetadataBuilder::addTrivialCopy(const std::byte* buffer, uint64_t size) {
  header_.productFlags |= HasTrivialCopy;
  append<uint8_t>(static_cast<uint8_t>(ProductMetadata::Kind::TrivialCopy));
  append<uint64_t>(size);
  appendBytes(buffer, size);
}

const uint8_t* ProductMetadataBuilder::data() const { return buffer_; }
uint8_t* ProductMetadataBuilder::data() { return buffer_; }
size_t ProductMetadataBuilder::size() const { return size_; }
std::span<const uint8_t> ProductMetadataBuilder::buffer() const { return {buffer_, size_}; }

void ProductMetadataBuilder::receiveMetadata(int src, int tag, MPI_Comm comm) {
  MPI_Status status;
  MPI_Recv(buffer_, maxMetadataSize_, MPI_BYTE, src, tag, comm, &status);
  // add error handling if message is too long (quite unlikely to happen so far)
  int receivedBytes = 0;
  MPI_Get_count(&status, MPI_BYTE, &receivedBytes);
  assert(static_cast<size_t>(receivedBytes) >= headerSize_ && "received metadata was less than header size");
  memcpy(&header_, buffer_, sizeof(header_));
  size_ = receivedBytes;
  readOffset_ = headerSize_;
}

ProductMetadata ProductMetadataBuilder::getNext() {
  if (readOffset_ >= size_)
    throw std::out_of_range("No more metadata entries");

  ProductMetadata meta;
  auto kind = static_cast<ProductMetadata::Kind>(consume<uint8_t>());
  meta.kind = kind;

  switch (kind) {
    case ProductMetadata::Kind::Missing:
      break;

    case ProductMetadata::Kind::Serialized:
      meta.sizeMeta = consume<uint64_t>();
      break;

    case ProductMetadata::Kind::TrivialCopy: {
      uint64_t blobSize = consume<uint64_t>();
      if (readOffset_ + blobSize > size_) {
        throw std::runtime_error("Metadata buffer too short for trivialCopy data");
      }
      meta.sizeMeta = blobSize;
      meta.trivialCopyOffset = buffer_ + readOffset_;
      readOffset_ += blobSize;
      break;
    }

    default:
      throw std::runtime_error("Unknown metadata kind");
  }

  return meta;
}

void ProductMetadataBuilder::resizeBuffer(size_t newCap) {
  uint8_t* newBuf = static_cast<uint8_t*>(std::realloc(buffer_, newCap));
  if (!newBuf)
    throw std::bad_alloc();
  buffer_ = newBuf;
  capacity_ = newCap;
}

void ProductMetadataBuilder::ensureCapacity(size_t needed) {
  if (size_ + needed <= capacity_)
    return;

  size_t newCapacity = capacity_ ? capacity_ : 64;
  while (size_ + needed > newCapacity)
    newCapacity *= 2;

  uint8_t* newData = static_cast<uint8_t*>(std::realloc(buffer_, newCapacity));
  if (!newData)
    throw std::bad_alloc();
  buffer_ = newData;
  capacity_ = newCapacity;
}

void ProductMetadataBuilder::appendBytes(const std::byte* src, size_t size) {
  ensureCapacity(size);
  std::memcpy(buffer_ + size_, src, size);
  size_ += size;
}

void ProductMetadataBuilder::debugPrintMetadataSummary() const {
  if (size_ < headerSize_) {
    std::cerr << "ERROR: Buffer too small to contain metadata header\n";
    return;
  }

  std::ostringstream out;

  out << "---- ProductMetadata Debug Summary ----\n";
  out << "Header:\n";
  out << "  Product count:           " << header_.productCount << "\n";
  out << "  Serialized buffer size:  " << header_.serializedBufferSize << " bytes\n";
  out << "  Flags:";
  if (hasMissing())
    out << " Missing";
  if (hasSerialized())
    out << " Serialized";
  if (hasTrivialCopy())
    out << " TrivialCopy";
  out << "\n\n";

  // Safe copy for reading
  ProductMetadataBuilder reader(*this);
  reader.readOffset_ = headerSize_;

  size_t count = 0;
  size_t numMissing = 0;
  size_t numSerialized = 0;
  size_t numTrivial = 0;

  try {
    while (count < static_cast<size_t>(header_.productCount)) {
      ProductMetadata meta = reader.getNext();
      ++count;

      out << "Product #" << count << ": ";

      switch (meta.kind) {
        case ProductMetadata::Kind::Missing:
          ++numMissing;
          out << "Missing\n";
          break;

        case ProductMetadata::Kind::Serialized:
          ++numSerialized;
          out << "Serialized, size = " << meta.sizeMeta << "\n";
          break;

        case ProductMetadata::Kind::TrivialCopy:
          ++numTrivial;
          out << "TrivialCopy, size = " << meta.sizeMeta << "\n";
          break;
      }
    }
  } catch (const std::exception& e) {
    out << "\nERROR while parsing metadata: " << e.what() << "\n";
  }

  out << "\n----------------------------------------\n";
  out << "Total entries parsed:   " << count << "\n";
  out << "  Missing:              " << numMissing << "\n";
  out << "  Serialized:           " << numSerialized << "\n";
  out << "  TrivialCopy:          " << numTrivial << "\n";
  out << "Total metadata size:    " << size_ << " bytes\n";

  std::cerr << out.str() << std::flush;
}
