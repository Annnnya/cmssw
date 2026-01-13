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
process.options.numberOfConcurrentLuminosityBlocks = 2


# FastTimer output
experiment_name = os.environ.get("EXPERIMENT_NAME", "unnamed")
output_dir = os.environ.get("EXPERIMENT_OUTPUT_DIR", "../../test_results/one_time_tests/")


process.FastTimerService = _process.FastTimerService.clone()
process.FastTimerService.writeJSONSummary = True
process.FastTimerService.jsonFileName=cms.untracked.string(f"{output_dir}/remote_{experiment_name}.json")

process.ThroughputService = _process.ThroughputService.clone()
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

# HBHE local reconstruction from the HLT menu
process.hltHcalDigis = _process.hltHcalDigis.clone()
process.hltHcalDigisSoA = _process.hltHcalDigisSoA.clone()
process.hltHbheRecoSoA = _process.hltHbheRecoSoA.clone()

process.hltParticleFlowRecHitHBHESoA = _process.hltParticleFlowRecHitHBHESoA.clone()
process.hltParticleFlowClusterHBHESoA = _process.hltParticleFlowClusterHBHESoA.clone()

# run the HBHE local reconstruction
process.HLTLocalHBHE = cms.Path(
    process.hltGetRaw +
    process.hltHcalDigis +
    process.hltHcalDigisSoA +
    process.hltHbheRecoSoA +
    process.hltParticleFlowRecHitHBHESoA +
    process.hltParticleFlowClusterHBHESoA
)

# ECAL local reconstruction from the HLT menu
process.hltEcalDigisSoA = _process.hltEcalDigisSoA.clone()
process.hltEcalUncalibRecHitSoA = _process.hltEcalUncalibRecHitSoA.clone()


# run the ECAL local reconstruction
process.HLTLocalECAL = cms.Path(
    process.hltGetRaw +
    process.hltEcalDigisSoA +
    process.hltEcalUncalibRecHitSoA
)

# Pixel local reconstruction from the HLT menu
process.hltOnlineBeamSpot = _process.hltOnlineBeamSpot.clone()
process.hltOnlineBeamSpotDevice = _process.hltOnlineBeamSpotDevice.clone()
process.hltSiPixelClustersSoA = _process.hltSiPixelClustersSoA.clone()
process.hltSiPixelRecHitsSoA = _process.hltSiPixelRecHitsSoA.clone()
process.hltPixelTracksSoA = _process.hltPixelTracksSoA.clone()
process.hltPixelVerticesSoA = _process.hltPixelVerticesSoA.clone()


process.HLTLocalPixel = cms.Path(
    process.hltGetRaw +
    process.hltOnlineBeamSpot +
    process.hltOnlineBeamSpotDevice +
    process.hltSiPixelClustersSoA +
    process.hltSiPixelRecHitsSoA +
    process.hltPixelTracksSoA +
    process.hltPixelVerticesSoA 
)

# schedule the reconstruction
process.schedule = cms.Schedule(
    process.HLTriggerFirstPath,
    # process.Status_OnCPU,
    process.Status_OnGPU,
    process.HLTLocalHBHE,
    process.HLTLocalECAL,
    process.HLTLocalPixel
)

# process.Tracer = cms.Service("Tracer")
