# OpenAudioBooksIPad

iPad-first MVP audiobook builder using **SwiftUI + SwiftData + AVFoundation** with a modular TTS layer designed for free/open-source engines.

## Why this architecture

- **MVVM + service layer + repository layer** keeps SwiftUI views lean and testable.
- **SwiftData** was selected over Core Data for MVP speed and clean model declarations with modern Swift syntax.
- **Protocol-based TTS abstraction** lets us ship a working default path now while making Piper/Coqui integration a drop-in replacement later.

## High-level architecture

```
SwiftUI Views
   -> ViewModels (@MainActor)
      -> Service Protocols (ImportService, PlaybackService, TextToSpeechEngine)
         -> Concrete Services (DefaultImportService, DefaultPlaybackService, TTSQueueService)
            -> Repository (SwiftDataAudiobookRepository, SwiftDataSettingsRepository)
               -> SwiftData Store + local files (GeneratedAudio/*)
```

## Project structure

```
OpenAudioBooksIPad/
  OpenAudioBooksIPad/
    App/
    Core/
    Domain/
      Models/
      Protocols/
    Data/
      Repositories/
    Services/
      Import/
      TTS/
      Queue/
      Playback/
    Features/
      Library/
      BookDetail/
      Import/
      Player/
      Settings/
    Resources/SampleData/
  OpenAudioBooksIPadTests/
```

## Current MVP capabilities

- Import from pasted text and files (`.txt`, `.pdf`; `.epub` scaffolded).
- Parse text into chapters and chunks for long-form synthesis.
- Queue chapter segment generation with persistent status fields.
- Play generated segments with basic transport controls.
- Persist settings and playback progress.
- iPad-friendly split layout (`NavigationSplitView`).

## TTS implementation status

### Default (included)
- `MockTTSEngine`: deterministic development engine to validate full app flow.

### Open-source adapter path (included)
- `LocalHTTPPiperAdapter`: targets a local Piper-compatible endpoint (`http://127.0.0.1:5002/synthesize`).
- This adapter is intentionally isolated behind `TextToSpeechEngine`.

## Integrating real Piper

1. Run Piper in a local service process that accepts `POST /synthesize` with `{ text, voice }` and returns WAV bytes.
2. Point `LocalHTTPPiperAdapter.baseURL` to that service.
3. Ensure output WAV format is iOS-playable (PCM 16-bit, standard sample rate).
4. Replace `MockTTSEngine` as default in `AppDependencies` once stable.

## Known limitations

- Mock engine writes placeholder text data instead of true audio.
- Lock-screen / remote command center support is not fully wired.
- EPUB parsing is scaffold-only in this pass.
- TTS queue currently processes sequentially (safe default for MVP).

## Next steps

- Add true WAV generation in default free engine path (Piper local runtime/bridge).
- Introduce background task scheduling + retry policy for generation jobs.
- Add chapter-level waveform/progress UI and richer player timeline.
- Add robust EPUB parser and metadata extraction.
