import FWCore.ParameterSet.Config as cms
import os

import sys
sys.path.insert(0, '..')


from hlt import process as _process

from HLTrigger.Configuration.common import *


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
# experiment_name = os.environ.get("EXPERIMENT_NAME", "unnamed")
# output_dir = os.environ.get("EXPERIMENT_OUTPUT_DIR", "../../test_results/one_time_tests/")


# process.FastTimerService = _process.FastTimerService.clone()
# process.FastTimerService.writeJSONSummary = True
# process.FastTimerService.jsonFileName=cms.untracked.string(f"{output_dir}/remote_{experiment_name}.json")
process.FastTimerService = _process.FastTimerService.clone()
process.FastTimerService.writeJSONSummary = True
process.FastTimerService.jsonFileName=cms.untracked.string(f"../../../test_results/results_mpio1.json")

process.ThroughputService = cms.Service('ThroughputService',
    enableDQM = cms.untracked.bool(False),
    printEventSummary = cms.untracked.bool(True),
    eventResolution = cms.untracked.uint32(10),
    eventRange = cms.untracked.uint32(10300),
)

process.MessageLogger.cerr.ThroughputService = cms.untracked.PSet(
    limit = cms.untracked.int32(10000000),
    reportEvery = cms.untracked.int32(1)
)

# process.ThroughputService.printEventSummary = True
# process.load("FWCore/Services/Tracer_cfi")


process.hltGetRaw = cms.EDAnalyzer( "HLTGetRaw",
    RawDataCollection = cms.InputTag( "rawDataCollector" )
)
process.hltPSetMap = cms.EDProducer( "ParameterSetBlobProducer" )
process.hltBoolFalse = cms.EDFilter( "HLTBool",
    result = cms.bool( False )
)
process.hltBackend = cms.EDProducer( "AlpakaBackendProducer@alpaka"
)
process.hltStatusOnGPUFilter = cms.EDFilter( "AlpakaBackendFilter",
    producer = cms.InputTag( 'hltBackend','backend' ),
    backends = cms.vstring( 'CudaAsync',
      'ROCmAsync' )
)

process.HLTriggerFirstPath = cms.Path( process.hltGetRaw + process.hltPSetMap + process.hltBoolFalse )
process.Status_OnCPU = cms.Path( process.hltBackend + ~process.hltStatusOnGPUFilter )
process.Status_OnGPU = cms.Path( process.hltBackend + process.hltStatusOnGPUFilter )

process.DQMStore = _process.DQMStore.clone()
process.EvFDaqDirector = _process.EvFDaqDirector.clone()
process.source = _process.source.clone()
process.maxEvents.input = 1000






# set up the MPI communication channel
process.load("HeterogeneousCore.MPIServices.MPIService_cfi")
process.MPIService.pmix_server_uri = "file:server.uri"

from HeterogeneousCore.MPICore.mpiController_cfi import mpiController as mpiController_

process.mpiController0 = mpiController_.clone(
    remote_process_rank = 0
)

process.mpiController1 = mpiController_.clone(
    remote_process_rank = 1
)

process.mpiController2 = mpiController_.clone(
    remote_process_rank = 2
)


# process.load("FWCore/Services/Tracer_cfi")

# send the raw data over MPI
process.mpiSenderRawData0 = cms.EDProducer("MPISender",
    upstream = cms.InputTag("mpiController0"),
    instance = cms.int32(1),
    products = cms.vstring("rawDataCollector")
)

process.mpiSenderRawData1 = cms.EDProducer("MPISender",
    upstream = cms.InputTag("mpiController1"),
    instance = cms.int32(1),
    products = cms.vstring("rawDataCollector")
)

process.mpiSenderRawData2 = cms.EDProducer("MPISender",
    upstream = cms.InputTag("mpiController2"),
    instance = cms.int32(1),
    products = cms.vstring("rawDataCollector")
)



# process.hltEcalDigisSoAFilter = cms.EDFilter("PathStateRelease",
#     state = cms.InputTag("hltEcalDigisSoA")
#     )

# insert_modules_before(process, process.hltEcalDigisSoA, process.hltEcalDigisSoAFilter)

# del process.hltEcalDigisSoA

# receive the ECAL digis SoA over MPI
process.hltEcalDigisSoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("mpiSenderRawData1"),
    instance = cms.int32(20),
    products = cms.VPSet(cms.PSet(
        type = cms.string("PortableHostCollection<EcalDigiSoALayout<128,false> >"),
        label = cms.string("ebDigis")
    ), cms.PSet(
        type = cms.string("PortableHostCollection<EcalDigiSoALayout<128,false> >"),
        label = cms.string("eeDigis")
    ), cms.PSet(
       type = cms.string("ushort"),
       label = cms.string("backend")
    )
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # )
    )
)

# process.hltEcalUncalibRecHitSoAFilter = cms.EDFilter("PathStateRelease",
#     state = cms.InputTag("hltEcalUncalibRecHitSoA")
#     )

# insert_modules_before(process, process.hltEcalUncalibRecHitSoA, process.hltEcalUncalibRecHitSoAFilter)

# del process.hltEcalUncalibRecHitSoA

# receive the ECAL uncalibrated rechits SoA over MPI
process.hltEcalUncalibRecHitSoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("hltEcalDigisSoA"),
    instance = cms.int32(21),
    products = cms.VPSet(cms.PSet(
        type = cms.string("PortableHostCollection<EcalUncalibratedRecHitSoALayout<128,false> >"),
        label = cms.string("EcalUncalibRecHitsEB")
    ), cms.PSet(
        type = cms.string("PortableHostCollection<EcalUncalibratedRecHitSoALayout<128,false> >"),
        label = cms.string("EcalUncalibRecHitsEE")
    ), cms.PSet(
       type = cms.string("ushort"),
       label = cms.string("backend")
    )
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # )
    )
)


# process.hltHbheRecoSoAFilter = cms.EDFilter("PathStateRelease",
#     state = cms.InputTag("hltHbheRecoSoA")
#     )

# insert_modules_before(process, process.hltHbheRecoSoA, process.hltHbheRecoSoAFilter)

# del process.hltHbheRecoSoA

# receive the HBHE rechits SoA over MPI
process.hltHbheRecoSoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("mpiSenderRawData0"),
    instance = cms.int32(11),
    products = cms.VPSet(cms.PSet(
        type = cms.string("PortableHostCollection<hcal::HcalRecHitSoALayout<128,false> >"),
        label = cms.string("")
    ), cms.PSet(
       type = cms.string("ushort"),
       label = cms.string("backend")
    )
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # )
    )
)

# process.hltParticleFlowRecHitHBHESoAFilter = cms.EDFilter("PathStateRelease",
#     state = cms.InputTag("hltParticleFlowRecHitHBHESoA")
#     )

# insert_modules_before(process, process.hltParticleFlowRecHitHBHESoA, process.hltParticleFlowRecHitHBHESoAFilter)

# del process.hltParticleFlowRecHitHBHESoA

# receive the HBHE PF rechits SoA over MPI
process.hltParticleFlowRecHitHBHESoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("hltHbheRecoSoA"),
    instance = cms.int32(12),
    products = cms.VPSet(cms.PSet(
        type = cms.string("PortableHostCollection<reco::PFRecHitSoALayout<128,false> >"),
        label = cms.string("")
    ), cms.PSet(
       type = cms.string("ushort"),
       label = cms.string("backend")
    ))
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # ))
)

# process.hltParticleFlowClusterHBHESoAFilter = cms.EDFilter("PathStateRelease",
#     state = cms.InputTag("hltParticleFlowClusterHBHESoA")
#     )

# insert_modules_before(process, process.hltParticleFlowClusterHBHESoA, process.hltParticleFlowClusterHBHESoAFilter)

# del process.hltParticleFlowClusterHBHESoA

# receive the HBHE PF clusters SoA over MPI
process.hltParticleFlowClusterHBHESoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("hltParticleFlowRecHitHBHESoA"),
    instance = cms.int32(13),
    products = cms.VPSet(cms.PSet(
        type = cms.string("PortableHostCollection<reco::PFClusterSoALayout<128,false> >"),
        label = cms.string("")
    ), cms.PSet(
        type = cms.string("PortableHostCollection<reco::PFRecHitFractionSoALayout<128,false> >"),
        label = cms.string("")
    ), cms.PSet(
       type = cms.string("ushort"),
       label = cms.string("backend")
    ))
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # ))
)

# del process.hltSiPixelClustersSoA

# receive the SiPixelClustersSoA over MPI
process.hltSiPixelClustersSoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("mpiSenderRawData2"),
    instance = cms.int32(32),
    products = cms.VPSet(
    cms.PSet(
        type = cms.string("SiPixelClustersHost"),
        label = cms.string("")
    ), cms.PSet(
        type = cms.string("SiPixelDigisHost"),
        label = cms.string("")
    ), cms.PSet(
        type = cms.string("SiPixelDigiErrorsHost"),
        label = cms.string("")
    ), cms.PSet(
        type = cms.string("std::map<unsigned int,std::vector<SiPixelRawDataError> >"),
        label = cms.string("")
    ), cms.PSet(
        type = cms.string("ushort"),
        label = cms.string("backend")
    ))
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # ))
)


# del process.hltSiPixelRecHitsSoA

# receive the SiPixelRecHitsSoA over MPI
process.hltSiPixelRecHitsSoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("hltSiPixelClustersSoA"),
    instance = cms.int32(33),
    products = cms.VPSet(
    cms.PSet(
        type = cms.string("reco::TrackingRecHitHost"),
        label = cms.string("")
    ), cms.PSet(
        type = cms.string("ushort"),
        label = cms.string("backend")
    ))
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # ))
)

# del process.hltPixelTracksSoA

# receive the PixelTracksSoA over MPI
process.hltPixelTracksSoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("hltSiPixelRecHitsSoA"),
    instance = cms.int32(34),
    products = cms.VPSet(cms.PSet(
        type = cms.string("reco::TracksHost"),
        label = cms.string("")
    ), cms.PSet(
        type = cms.string("ushort"),
        label = cms.string("backend")
    )
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # ),
  )
)

# del process.hltPixelVerticesSoA

# receive the PixelVerticesSoA over MPI
process.hltPixelVerticesSoA = cms.EDProducer("MPIReceiver",
    upstream = cms.InputTag("hltPixelTracksSoA"),
    instance = cms.int32(35),
    products = cms.VPSet(cms.PSet(
        type = cms.string("ZVertexHost"),
        label = cms.string("")
    ), cms.PSet(
       type = cms.string("ushort"),
       label = cms.string("backend")
    )
    # cms.PSet(
    #     type = cms.string("edm::PathStateToken"),
    #     label = cms.string("")
    # )
    )
)

# General path state to validate if the event is active (sometimes it's not apparently)
# process.rawDataCollectorActivity = cms.EDProducer("PathStateCapture")

# StateCapture for remote path HLTLocalECAL 
# process.EcalDigisAndRecoActivity = cms.EDProducer("PathStateCapture")

# StateCapture for remote path HLTLocalHBHE
# process.hltHbheRecoSoAAParticleFlowActivity = cms.EDProducer("PathStateCapture")

# StateCapture for remote path HLTLocalPixel
# process.PixelActivity = cms.EDProducer("PathStateCapture")


# schedule the communication before the ECAL local reconstruction
# process.HLTDoFullUnpackingEgammaEcalWithoutPreshowerSequence.insert(0, process.rawDataCollectorActivity) # hltEcalDigisSoA hltEcalUncalibRecHitSoA
# process.HLTDoFullUnpackingEgammaEcalWithoutPreshowerSequence.insert(1, process.EcalDigisAndRecoActivity)


# HLTLocalHBHE remote path should run if any of its products will be needed:
# schedule the communication before the HBHE local reconstruction
# process.HLTDoLocalHcalSequence.insert(0, process.rawDataCollectorActivity) # hltHbheRecoSoA
# process.HLTDoLocalHcalSequence.insert(1, process.hltHbheRecoSoAAParticleFlowActivity)

# process.HLTStoppedHSCPLocalHcalReco.insert(0, process.rawDataCollectorActivity) # hltHbheRecoSoA
# process.HLTStoppedHSCPLocalHcalReco.insert(1, process.hltHbheRecoSoAAParticleFlowActivity)

# # schedule the communication before the HBHE PF reconstruction
# process.HLTPFHcalClustering.insert(0, process.rawDataCollectorActivity) # hltParticleFlowRecHitHBHESoA hltParticleFlowClusterHBHESoA
# process.HLTPFHcalClustering.insert(1, process.hltHbheRecoSoAAParticleFlowActivity)

# # schedule the communication before the Pixel local reconstruction
# process.HLTDoLocalPixelSequence.insert(0, process.rawDataCollectorActivity) # pixel tracking
# process.HLTDoLocalPixelSequence.insert(1, process.PixelActivity)

# process.mpiSenderEcalDigisAndRecoActivity = cms.EDProducer("MPISender",
#     upstream = cms.InputTag("mpiController"),
#     instance = cms.int32(2),
#     products = cms.vstring("EcalDigisAndRecoActivity")
# )


# process.mpiSenderhltHbheRecoSoAAParticleFlowActivity = cms.EDProducer("MPISender",
#     upstream = cms.InputTag("mpiController"),
#     instance = cms.int32(3),
#     products = cms.vstring("hltHbheRecoSoAAParticleFlowActivity")
# )

# process.mpiSenderPixelActivity = cms.EDProducer("MPISender",
#     upstream = cms.InputTag("mpiController"),
#     instance = cms.int32(4),
#     products = cms.vstring("PixelActivity")
# )


# schedule the communication for every event
process.Offload = cms.Path(
    process.mpiController0 +
    process.mpiController1 +
    process.mpiController2 +
    process.mpiSenderRawData0 +
    process.mpiSenderRawData1 +
    process.mpiSenderRawData2 +
    # process.mpiSenderEcalDigisAndRecoActivity +
    # process.mpiSenderhltHbheRecoSoAAParticleFlowActivity +
    # process.mpiSenderPixelActivity +
    process.hltHbheRecoSoA +
    process.hltParticleFlowRecHitHBHESoA +
    process.hltParticleFlowClusterHBHESoA +
    process.hltEcalDigisSoA +
    process.hltEcalUncalibRecHitSoA +
    process.hltSiPixelClustersSoA +
    process.hltSiPixelRecHitsSoA +
    process.hltPixelTracksSoA +
    process.hltPixelVerticesSoA
)

process.schedule = cms.Schedule(process.Offload)

# process.Tracer = cms.Service("Tracer")

process.ThroughputService = cms.Service('ThroughputService',
    enableDQM = cms.untracked.bool(False),
    printEventSummary = cms.untracked.bool(True),
    eventResolution = cms.untracked.uint32(10),
    eventRange = cms.untracked.uint32(10300),
)

# process.MessageLogger.cerr.ThroughputService = cms.untracked.PSet(
#     limit = cms.untracked.int32(10000000),
#     reportEvery = cms.untracked.int32(1)
# )
