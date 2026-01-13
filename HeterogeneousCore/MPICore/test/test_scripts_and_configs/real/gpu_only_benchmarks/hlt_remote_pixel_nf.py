import FWCore.ParameterSet.Config as cms

import os

import sys
sys.path.insert(0, '..')


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
    ))
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # ))
)


# process.activityFilterRawData = cms.EDFilter("PathStateRelease",
#     state = cms.InputTag("rawDataCollector")
#     )


# process.mpiReceiverPixelActivity = cms.EDProducer("MPIReceiver",
#     upstream = cms.InputTag("source"),
#     instance = cms.int32(4),
#     products = cms.VPSet(cms.PSet(
#         type = cms.string("edm::PathStateToken"),
#         label = cms.string("")
#     ))
# )

# process.activityFilterPixel = cms.EDFilter("PathStateRelease",
#     state = cms.InputTag("mpiReceiverPixelActivity")
#     )


process.hltGetRaw = _process.hltGetRaw.clone()

# Pixel local reconstruction from the HLT menu
process.hltOnlineBeamSpot = _process.hltOnlineBeamSpot.clone()
process.hltOnlineBeamSpotDevice = _process.hltOnlineBeamSpotDevice.clone()
process.hltSiPixelClustersSoA = _process.hltSiPixelClustersSoA.clone()
process.hltSiPixelRecHitsSoA = _process.hltSiPixelRecHitsSoA.clone()
process.hltPixelTracksSoA = _process.hltPixelTracksSoA.clone()
process.hltPixelVerticesSoA = _process.hltPixelVerticesSoA.clone()

# send the SiPixelClustersSoA over MPI
process.mpiSenderSiPixelClustersSoA = cms.EDProducer("MPISender",
    upstream = cms.InputTag("rawDataCollector"),
    instance = cms.int32(32),
    products = cms.vstring(
        "SiPixelClustersHost_hltSiPixelClustersSoA__*",
        "SiPixelDigisHost_hltSiPixelClustersSoA__*",
        "SiPixelDigiErrorsHost_hltSiPixelClustersSoA__*",
        "uintSiPixelRawDataErrorsstdmap_hltSiPixelClustersSoA__*",
        "ushort_hltSiPixelClustersSoA_backend_*"
        # "*_PixelActivity__*"
    )
)


# send the SiPixelRecHitsSoA over MPI
process.mpiSenderSiPixelRecHitsSoA = cms.EDProducer("MPISender",
    upstream = cms.InputTag("mpiSenderSiPixelClustersSoA"),
    instance = cms.int32(33),
    products = cms.vstring(
        "recoTrackingRecHitHost_hltSiPixelRecHitsSoA__*",
        "ushort_hltSiPixelRecHitsSoA_backend_*"
        # "*_PixelActivity__*",
    )
)

# send the PixelTracksSoA over MPI
process.mpiSenderPixelTracksSoA = cms.EDProducer("MPISender",
    upstream = cms.InputTag("mpiSenderSiPixelRecHitsSoA"),
    instance = cms.int32(34),
    products = cms.vstring(
        "128falserecoTrackLayout128falserecoTrackHitsLayoutPortableHostMultiCollection_hltPixelTracksSoA__*",
        "ushort_hltPixelTracksSoA_backend_*"
        # "*_PixelActivity__*",
    )
)

# send the PixelVerticesSoA over MPI
process.mpiSenderPixelVerticesSoA = cms.EDProducer("MPISender",
    upstream = cms.InputTag("mpiSenderPixelTracksSoA"),
    instance = cms.int32(35),
    products = cms.vstring(
        "128falserecoZVertexLayout128falserecoZVertexTracksLayoutPortableHostMultiCollection_hltPixelVerticesSoA__*",
        "ushort_hltPixelVerticesSoA_backend_*"
        # "*_PixelActivity__*",
    )
)

# process.PixelActivity = cms.EDProducer("PathStateCapture")

# run the Pixel local reconstruction
process.HLTLocalPixel = cms.Path(
    # process.activityFilterRawData +
    # process.activityFilterPixel +
    process.hltGetRaw +
    process.hltOnlineBeamSpot +
    process.hltOnlineBeamSpotDevice +
    process.hltSiPixelClustersSoA +
    process.hltSiPixelRecHitsSoA +
    process.hltPixelTracksSoA +
    process.hltPixelVerticesSoA
    # process.PixelActivity
)

process.MPIPath = cms.Path(
    process.rawDataCollector +
    # process.mpiReceiverEcalDigisActivity +
    # process.mpiReceiverhltHbheRecoSoAAParticleFlowActivity +
    # process.mpiReceiverPixelActivity +
    # process.mpiSenderEcalDigisSoA +
    # process.mpiSenderEcalUncalibRecHitSoA +
    # process.mpiSenderHbheRecoSoA +
    # process.mpiSenderParticleFlowRecHitHBHESoA +
    # process.mpiSenderParticleFlowClusterHBHESoA +
    process.mpiSenderSiPixelClustersSoA +
    process.mpiSenderSiPixelRecHitsSoA +
    process.mpiSenderPixelTracksSoA +
    process.mpiSenderPixelVerticesSoA
)

# schedule the reconstruction
process.schedule = cms.Schedule(
    # process.HLTLocalHBHE,
    # process.HLTLocalECAL,
    process.HLTLocalPixel,
    process.MPIPath
)

# process.Tracer = cms.Service("Tracer")