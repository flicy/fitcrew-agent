import Foundation
import Testing
@testable import FitCrewHealthCore

@Test func pairingURLDecodesOnlyAnExchangeInvitation() throws {
    let json = """
    {"baseURL":"https://bodyos.example.test","expiresAt":"2099-01-01T00:00:00+00:00","pairingCode":"high-entropy-opaque-pairing-code-1234567890"}
    """
    let encoded = Data(json.utf8).base64EncodedString()
        .replacingOccurrences(of: "+", with: "-")
        .replacingOccurrences(of: "/", with: "_")
        .replacingOccurrences(of: "=", with: "")
    let url = URL(string: "fitcrew-health://configure?payload=\(encoded)")!

    let invitation = try PairingDecoder.decode(url)

    #expect(invitation.baseURL.absoluteString == "https://bodyos.example.test")
    #expect(invitation.pairingCode == "high-entropy-opaque-pairing-code-1234567890")
    #expect(invitation.expiresAt > Date())
}

@Test func pairingRejectsDirectProvisioningSecrets() {
    let json = """
    {"baseURL":"https://bodyos.example.test","deviceToken":"secret","expiresAt":"2099-01-01T00:00:00+00:00","pairingCode":"high-entropy-opaque-pairing-code-1234567890"}
    """
    let encoded = Data(json.utf8).base64EncodedString()
        .replacingOccurrences(of: "+", with: "-")
        .replacingOccurrences(of: "/", with: "_")
        .replacingOccurrences(of: "=", with: "")

    #expect(throws: PairingError.invalidPayload) {
        try PairingDecoder.decode(URL(string: "fitcrew-health://configure?payload=\(encoded)")!)
    }
}

@Test func pairingRejectsUnexpectedSchemes() {
    #expect(throws: PairingError.invalidURL) {
        try PairingDecoder.decode(URL(string: "https://example.test/configure?payload=nope")!)
    }
}
