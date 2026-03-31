import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var viewModel: SettingsViewModel

    var body: some View {
        Form {
            Section("TTS Engine") {
                Picker("Engine", selection: $viewModel.settings.selectedEngineID) {
                    ForEach(viewModel.engines, id: \.id) { engine in
                        Text(engine.displayName).tag(engine.id)
                    }
                }

                Picker("Voice", selection: $viewModel.settings.selectedVoiceID) {
                    ForEach(viewModel.ttsEngineManager.selectedEngine.availableVoices) { voice in
                        Text("\(voice.displayName) (\(voice.locale))").tag(voice.id)
                    }
                }
            }

            Section("Synthesis") {
                Stepper(value: $viewModel.settings.chunkSize, in: 300...2000, step: 100) {
                    Text("Chunk size: \(viewModel.settings.chunkSize)")
                }
                Toggle("Enable local network TTS", isOn: $viewModel.settings.enableNetworkTTS)
            }

            Section("Playback") {
                Slider(value: $viewModel.settings.speechRate, in: 0.8...1.5, step: 0.1)
                Text("Default speed: \(viewModel.settings.speechRate, specifier: "%.1fx")")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Settings")
        .onDisappear {
            viewModel.save()
        }
    }
}
