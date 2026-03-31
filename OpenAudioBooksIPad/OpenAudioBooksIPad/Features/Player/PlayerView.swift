import SwiftUI

struct PlayerView: View {
    @ObservedObject var viewModel: PlayerViewModel

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text(viewModel.selectedBook?.title ?? "No Book")
                    .font(.title2)

                HStack(spacing: 30) {
                    Button {
                        viewModel.seek(seconds: -15)
                    } label: {
                        Label("Back 15", systemImage: "gobackward.15")
                    }

                    Button {
                        viewModel.playPause()
                    } label: {
                        Image(systemName: "playpause.fill")
                            .font(.system(size: 44))
                    }

                    Button {
                        viewModel.seek(seconds: 30)
                    } label: {
                        Label("Forward 30", systemImage: "goforward.30")
                    }
                }

                VStack {
                    Text("Playback Speed")
                    Picker("Rate", selection: $viewModel.rate) {
                        Text("0.8x").tag(Float(0.8))
                        Text("1.0x").tag(Float(1.0))
                        Text("1.2x").tag(Float(1.2))
                        Text("1.5x").tag(Float(1.5))
                    }
                    .pickerStyle(.segmented)
                    .onChange(of: viewModel.rate) { _, newValue in
                        viewModel.updateRate(newValue)
                    }
                }
                .padding(.horizontal)

                Spacer()
            }
            .padding()
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        viewModel.isPlayerPresented = false
                    }
                }
            }
        }
    }
}
