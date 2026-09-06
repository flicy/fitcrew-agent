import XCTest
@testable import FitCrewHealthCore

final class ProductTests: XCTestCase {
    func testEmptyStatePreservesMissingHealth() throws {
        let data = Data(#"{"journey":null,"experiments":[],"logs":[],"mission":null,"health":{"sample_count":0,"last_sync_at":null},"privacy_version":"2026-09-07"}"#.utf8)
        let state = try ProductState.decode(data)
        XCTAssertNil(state.journey)
        XCTAssertNil(state.health.lastSyncAt)
        XCTAssertEqual(state.health.sampleCount, 0)
    }

    func testExperimentOnlyOffersValidTransitions() throws {
        let data = Data(#"{"id":"test","title":"Sleep","hypothesis":"Earlier sleep","intervention":"Walk","metrics":["sleep"],"success_criteria":["more"],"stop_conditions":["pain"],"data_categories":["sleep"],"duration_days":7,"status":"proposed","revision":1,"source":"rule_based","result":null}"#.utf8)
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let experiment = try decoder.decode(ProductExperiment.self, from: data)
        XCTAssertEqual(experiment.actions, ["accept"])
        XCTAssertEqual(experiment.dataCategories, ["sleep"])
    }

    func testCheckValidationRejectsInvalidInput() {
        XCTAssertFalse(BodyCheckInput.isValid(energy: 0, stress: 1, note: ""))
        XCTAssertFalse(BodyCheckInput.isValid(energy: 3, stress: 4, note: ""))
        XCTAssertFalse(BodyCheckInput.isValid(energy: 3, stress: 1, note: String(repeating: "字", count: 501)))
        XCTAssertTrue(BodyCheckInput.isValid(energy: 3, stress: 1, note: "今天感觉不错"))
    }

    func testRealStateShapeDecodesMissionAndEvaluation() throws {
        let data = Data(#"{"journey":{"id":"j","goal":"sleep","title":"Sleep","start_date":"2026-09-07","days":90,"revision":1},"experiments":[{"id":"e","title":"Sleep","hypothesis":"Earlier sleep","intervention":"Walk","metrics":["sleep"],"success_criteria":["more"],"stop_conditions":["pain"],"data_categories":["sleep"],"duration_days":7,"status":"completed","revision":3,"source":"rule_based","result":{"summary":"Insufficient evidence","status":"insufficient","observed_days":2}}],"logs":[],"mission":{"id":"m","title":"Walk","status":"pending","date":"2026-09-07","why":"Move gently","revision":1},"health":{"sample_count":0,"last_sync_at":null},"privacy_version":"2026-09-07"}"#.utf8)
        let state = try ProductState.decode(data)
        XCTAssertEqual(state.mission?.why, "Move gently")
        XCTAssertEqual(state.journey?.days, 90)
        XCTAssertEqual(state.experiments.first?.actions, [])
        XCTAssertTrue(state.experiments.first?.result?.display.contains("Insufficient evidence") == true)
    }
}
