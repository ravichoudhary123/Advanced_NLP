import SwiftUI

struct RootView: View {
    @EnvironmentObject private var libraryVM: LibraryViewModel
    @EnvironmentObject private var playerVM: PlayerViewModel

    var body: some View {
        NavigationSplitView {
            LibraryView(viewModel: libraryVM)
        } detail: {
            if let selected = libraryVM.selectedBook {
                BookDetailView(book: selected)
            } else {
                ContentUnavailableView(
                    "No Book Selected",
                    systemImage: "books.vertical",
                    description: Text("Import text or PDF to generate your first audiobook.")
                )
            }
        }
        .sheet(isPresented: $playerVM.isPlayerPresented) {
            PlayerView(viewModel: playerVM)
        }
    }
}
