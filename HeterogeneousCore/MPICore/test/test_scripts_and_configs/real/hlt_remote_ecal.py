import FWCore.ParameterSet.Config as cms

import os

from hlt import process as _process

process = cms.Process("REMOTE")

process.load("Configuration.StandardSequences.Accelerators_cff")
# process.load("FWCore.MessageLogger.MessageLogger_cfi")

# load the event setup
for module in _process.psets.keys():
    setattr(process, module, getattr(_process, module).clone())
for module in _process.es_sources.keys():
    setattr(process, module, getattr(_process, module).clone())
for module in _process.es_producers.keys():
    setattr(process, module, getattr(_process, module).clone())


process.options.numberOfThreads = int(os.environ.get("EXPERIMENT_THREADS", 32))
process.options.numberOfStreams = int(os.environ.get("EXPERIMENT_STREAMS", 24))
process.options.numberOfConcurrentLuminosityBlocks = 1


# FastTimer output
experiment_name = os.environ.get("EXPERIMENT_NAME", "unnamed")
output_dir = os.environ.get("EXPERIMENT_OUTPUT_DIR", "../../test_results/one_time_tests/")


process.FastTimerService = _process.FastTimerService.clone()
process.FastTimerService.writeJSONSummary = True
process.FastTimerService.jsonFileName=cms.untracked.string(f"{output_dir}/remote_{experiment_name}.json")

process.ThroughputService = _process.ThroughputService.clone()
# process.ThroughputService.printEventSummary = True
# process.load("FWCore/Services/Tracer_cfi")

# set up the MPI communication channel
process.load("HeterogeneousCore.MPIServices.MPIService_cfi")
process.MPIService.pmix_server_uri = "file:server.uri"

process.source = cms.Source("MPISource",
  firstRun = cms.untracked.uint32(396102)
)
process.maxEvents.input = -1

# receive the raw data over MPI
process.rawDataCollector = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("source"),
    instance = cms.int32(1),
    products = cms.VPSet(cms.PSet(
    type = cms.string("FEDRawDataCollection"),
    label = cms.string("")
    ), cms.PSet(
        type = cms.string("edm::PathStateToken"),
        label = cms.string("")
    ))
)


process.activityFilterRawData = cms.EDFilter("PathStateRelease",
    state = cms.InputTag("rawDataCollector")
    )

process.mpiReceiverEcalDigisActivity = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("source"),
    instance = cms.int32(2),
    products = cms.VPSet(cms.PSet(
        type = cms.string("edm::PathStateToken"),
        label = cms.string("")
    ))
)

process.activityFilterEcalDigis = cms.EDFilter("PathStateRelease",
    state = cms.InputTag("mpiReceiverEcalDigisActivity")
    )

process.hltGetRaw = _process.hltGetRaw.clone()

# ECAL local reconstruction from the HLT menu
process.hltEcalDigisSoA = _process.hltEcalDigisSoA.clone()
process.hltEcalUncalibRecHitSoA = _process.hltEcalUncalibRecHitSoA.clone()

# send the ECAL digis SoA over MPI
process.mpiSenderEcalDigisSoA = cms.EDProducer("MPISender",
    upstream = cms.InputTag("rawDataCollector"),
    instance = cms.int32(20),
    products = cms.vstring(
        "128falseEcalDigiSoALayoutPortableHostCollection_hltEcalDigisSoA_ebDigis_*",
        "128falseEcalDigiSoALayoutPortableHostCollection_hltEcalDigisSoA_eeDigis_*",
        "ushort_hltEcalDigisSoA_backend_*",
        "*_ECALActivity__*",
    ) 
)

# send the ECAL uncalibrated rechits SoA over MPI
process.mpiSenderEcalUncalibRecHitSoA = cms.EDProducer("MPISender",
    upstream = cms.InputTag("mpiSenderEcalDigisSoA"),
    instance = cms.int32(21),
    products = cms.vstring(
        "128falseEcalUncalibratedRecHitSoALayoutPortableHostCollection_hltEcalUncalibRecHitSoA_EcalUncalibRecHitsEB_*",
        "128falseEcalUncalibratedRecHitSoALayoutPortableHostCollection_hltEcalUncalibRecHitSoA_EcalUncalibRecHitsEE_*",
        "ushort_hltEcalUncalibRecHitSoA_backend_*",
        "*_ECALActivity__*",
    ) 
)

process.ECALActivity = cms.EDProducer("PathStateCapture")

# run the ECAL local reconstruction
process.HLTLocalECAL = cms.Path(
    process.activityFilterRawData +
    process.activityFilterEcalDigis +
    process.hltGetRaw +
    process.hltEcalDigisSoA +
    process.hltEcalUncalibRecHitSoA +
    process.ECALActivity
)

process.MPIPath = cms.Path(
    process.rawDataCollector +
    process.mpiReceiverEcalDigisActivity +
    # process.mpiReceiverhltHbheRecoSoAAParticleFlowActivity +
    # process.mpiReceiverPixelActivity +
    process.mpiSenderEcalDigisSoA +
    process.mpiSenderEcalUncalibRecHitSoA
    # process.mpiSenderHbheRecoSoA +
    # process.mpiSenderParticleFlowRecHitHBHESoA +
    # process.mpiSenderParticleFlowClusterHBHESoA +
    # process.mpiSenderSiPixelClustersSoA +
    # process.mpiSenderSiPixelRecHitsSoA +
    # process.mpiSenderPixelTracksSoA +
    # process.mpiSenderPixelVerticesSoA
)

# schedule the reconstruction
process.schedule = cms.Schedule(
    # process.HLTLocalHBHE,
    process.HLTLocalECAL,
    # process.HLTLocalPixel,
    process.MPIPath
)

# process.Tracer = cms.Service("Tracer")