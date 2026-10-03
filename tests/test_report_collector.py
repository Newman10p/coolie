import unittest
from pathlib import Path

from report_collector import ComponentRecord, ReportCollectorController


class ReportCollectorTests(unittest.TestCase):
    def test_collects_snapshot_and_tracks_alerts(self):
        controller = ReportCollectorController()
        snapshot = controller.discover((
            ComponentRecord("brain", "core", "healthy", "platform"),
            ComponentRecord("research-room", "research", "warning", "ops"),
            ComponentRecord("orchestrator", "governance", "healthy", "ops"),
        )).snapshot
        self.assertEqual(snapshot.alert_count, 1)
        self.assertGreaterEqual(snapshot.health_ratio, 0.0)
        self.assertTrue(snapshot.orchestrator_ready)

    def test_discover_from_directory_reads_repo_components(self):
        repository_root = Path(__file__).resolve().parents[1]
        snapshot = ReportCollectorController().discover_from_directory(str(repository_root)).snapshot
        self.assertGreater(len(snapshot.components), 0)


if __name__ == "__main__":
    unittest.main()
