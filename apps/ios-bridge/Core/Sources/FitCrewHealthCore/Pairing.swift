import Foundation

public struct PairingInvitation: Equatable, Sendable {
    public let baseURL: URL
    public let pairingCode: String
    public let expiresAt: Date
}

public enum PairingError: Error, Equatable {
    case invalidURL
    case invalidPayload
}

public enum PairingDecoder {
    public static func decode(_ url: URL) throws -> PairingInvitation {
        guard url.scheme == "fitcrew-health", url.host == "configure",
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let encoded = components.queryItems?.first(where: { $0.name == "payload" })?.value
        else {
            throw PairingError.invalidURL
        }
        let normalized = encoded
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        let padded = normalized + String(repeating: "=", count: (4 - normalized.count % 4) % 4)
        guard let data = Data(base64Encoded: padded),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              Set(object.keys) == ["baseURL", "expiresAt", "pairingCode"],
              let baseURLString = object["baseURL"] as? String,
              let baseURL = URL(string: baseURLString),
              baseURL.scheme == "https",
              baseURL.host != nil,
              let pairingCode = object["pairingCode"] as? String,
              pairingCode.count >= 40,
              let expiresAtString = object["expiresAt"] as? String,
              let expiresAt = parseISO8601(expiresAtString),
              expiresAt > Date()
        else {
            throw PairingError.invalidPayload
        }
        return PairingInvitation(baseURL: baseURL, pairingCode: pairingCode, expiresAt: expiresAt)
    }

    private static func parseISO8601(_ value: String) -> Date? {
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = fractional.date(from: value) {
            return date
        }
        return ISO8601DateFormatter().date(from: value)
    }
}
