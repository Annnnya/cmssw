#ifndef HeterogeneousCore_MPICore_MPIToken_h
#define HeterogeneousCore_MPICore_MPIToken_h

#include <memory>

// forward declaration
class MPIChannel;

class MPIToken {
public:
  MPIToken() = default;

  explicit MPIToken(std::vector<std::shared_ptr<MPIChannel>> channels)
      : channels_(std::move(channels)) {}

  const std::vector<std::shared_ptr<MPIChannel>>& channels() const { return channels_; }

  MPIChannel* channel(size_t i = 0) const { return channels_.at(i).get(); }

private:
  std::vector<std::shared_ptr<MPIChannel>> channels_;
};


#endif  // HeterogeneousCore_MPICore_MPIToken_h
