#include "TrivialSerialisation/Common/interface/SerialiserFactory.h"
#include "TrivialSerialisation/Common/interface/Serialiser.h"

#include "DataFormats/Portable/interface/PortableHostObject.h"
#include "DataFormats/Portable/interface/PortableHostCollection.h"

#include "Eigen/Core"

#include "DataFormats/EcalDigi/interface/EcalDigiSoA.h"
#include "DataFormats/EcalRecHit/interface/EcalUncalibratedRecHitSoA.h"
#include "DataFormats/HcalRecHit/interface/HcalRecHitSoA.h"
#include "DataFormats/ParticleFlowReco/interface/PFRecHitSoA.h"
#include "DataFormats/ParticleFlowReco/interface/PFClusterSoA.h"
#include "DataFormats/ParticleFlowReco/interface/PFRecHitFractionSoA.h"


// DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollection<EcalDigiSoALayout<128,false> >);

// DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollection<EcalUncalibratedRecHitSoALayout<128,false> >);

// DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollection<hcal::HcalRecHitSoALayout<128,false> >);

// DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollection<reco::PFRecHitSoALayout<128,false> >);

// DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollection<reco::PFClusterSoALayout<128,false> >);

// DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollection<reco::PFRecHitFractionSoALayout<128,false> >);



using PortableHostCollectionEcalDigi = PortableHostCollection<EcalDigiSoALayout<128, false>>;
DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollectionEcalDigi);

using PortableHostCollectionEcalUncalibratedRecHit = PortableHostCollection<EcalUncalibratedRecHitSoALayout<128, false>>;
DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollectionEcalUncalibratedRecHit);

using PortableHostCollectionHcalRecHit = PortableHostCollection<hcal::HcalRecHitSoALayout<128, false>>;
DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollectionHcalRecHit);

using PortableHostCollectionPFRecHit = PortableHostCollection<reco::PFRecHitSoALayout<128, false>>;
DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollectionPFRecHit);

using PortableHostCollectionPFCluster = PortableHostCollection<reco::PFClusterSoALayout<128, false>>;
DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollectionPFCluster);

using PortableHostCollectionPFRecHitFraction = PortableHostCollection<reco::PFRecHitFractionSoALayout<128, false>>;
DEFINE_TRIVIAL_SERIALISER_PLUGIN(PortableHostCollectionPFRecHitFraction);
