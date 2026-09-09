import FitCrewHealthCore
import Foundation
import Testing
@testable import FitCrewHealthBridge

@MainActor
private final class PairingHarness {
    let suite = "fitcrew-pairing-tests-\(UUID().uuidString)"
    let defaults: UserDefaults
    let consent: ConsentStore
    var pending: [CheckedContinuation<PairingProvisioning, Error>] = []
    var tokens: [String] = []
    let origin = URL(string: "https://example.invalid")!

    init() throws {
        defaults = try #require(UserDefaults(suiteName: suite))
        consent = ConsentStore(defaults: defaults)
    }

    func makeModel() -> BridgeViewModel {
        BridgeViewModel(consentStore: consent, exchangeInvitation: { _ in
            try await withCheckedThrowingContinuation { self.pending.append($0) }
        }, writeToken: { self.tokens.append($0) })
    }

    func invitation() throws -> URL {
        let payload: [String: String] = [
            "baseURL": origin.absoluteString,
            "pairingCode": String(repeating: "synthetic", count: 8),
            "expiresAt": ISO8601DateFormatter().string(from: Date().addingTimeInterval(600))
        ]
        let encoded = try JSONSerialization.data(withJSONObject: payload).base64EncodedString()
            .replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_")
        var url = URLComponents(string: "fitcrew-health://configure")!
        url.queryItems = [URLQueryItem(name: "payload", value: encoded)]
        return try #require(url.url)
    }

    func response(baseURL: URL? = nil) -> PairingProvisioning {
        PairingProvisioning(baseURL: baseURL ?? origin, deviceBindingID: UUID(), consentIDs: [:], deviceToken: "synthetic")
    }

    func awaitRequests(_ count: Int) async throws {
        for _ in 0..<1000 { if pending.count == count { return }; await Task.yield() }
        throw URLError(.timedOut)
    }
}

@Test @MainActor func delayedPairingCannotReplaceNewLogin() async throws {
    let h = try PairingHarness()
    defer { h.defaults.removePersistentDomain(forName: h.suite) }
    let model = h.makeModel(), url = try h.invitation()
    let old = Task { await model.configure(from: url) }
    try await h.awaitRequests(1)
    let current = h.response()
    try model.install(current)
    let status = model.statusMessage
    h.pending[0].resume(returning: h.response())
    #expect(await old.value == false)
    #expect(h.consent.configuration?.deviceBindingID == current.deviceBindingID)
    #expect(h.tokens.count == 1)
    #expect(model.statusMessage == status)
}

@Test @MainActor func latestPairingWinsAndStaleFailureStaysSilent() async throws {
    let h = try PairingHarness()
    defer { h.defaults.removePersistentDomain(forName: h.suite) }
    let model = h.makeModel(), url = try h.invitation()
    let old = Task { await model.configure(from: url) }
    try await h.awaitRequests(1)
    let latest = Task { await model.configure(from: url) }
    try await h.awaitRequests(2)
    let response = h.response()
    h.pending[1].resume(returning: response)
    #expect(await latest.value)
    let status = model.statusMessage
    h.pending[0].resume(throwing: URLError(.notConnectedToInternet))
    #expect(await old.value == false)
    #expect(h.consent.configuration?.deviceBindingID == response.deviceBindingID)
    #expect(h.tokens.count == 1)
    #expect(model.statusMessage == status)
}

@Test @MainActor func supersededPairingCannotWinByFinishingFirst() async throws {
    let h = try PairingHarness()
    defer { h.defaults.removePersistentDomain(forName: h.suite) }
    let model = h.makeModel(), url = try h.invitation()
    let old = Task { await model.configure(from: url) }
    try await h.awaitRequests(1)
    let latest = Task { await model.configure(from: url) }
    try await h.awaitRequests(2)
    h.pending[0].resume(returning: h.response())
    #expect(await old.value == false)
    #expect(h.tokens.isEmpty)
    let response = h.response()
    h.pending[1].resume(returning: response)
    #expect(await latest.value)
    #expect(h.consent.configuration?.deviceBindingID == response.deviceBindingID)
}

@Test @MainActor func pairingCannotRedirectProvisionedServer() async throws {
    let h = try PairingHarness()
    defer { h.defaults.removePersistentDomain(forName: h.suite) }
    let model = h.makeModel(), url = try h.invitation()
    let attempt = Task { await model.configure(from: url) }
    try await h.awaitRequests(1)
    h.pending[0].resume(returning: h.response(baseURL: URL(string: "https://other.invalid")!))
    #expect(await attempt.value == false)
    #expect(h.tokens.isEmpty)
    #expect(h.consent.configuration == nil)
}
