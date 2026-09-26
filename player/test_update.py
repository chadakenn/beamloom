import unittest

import updater


class UpdateTest(unittest.TestCase):
    def test_a_restart_with_no_time_is_stuck(self):
        self.assertTrue(updater.update_is_stuck({"state": "restarting", "message": "Restarting into release 0.1.7."}, 1_000))
        self.assertFalse(updater.update_is_stuck({"state": "restarting", "at": 950}, 1_000))
        self.assertTrue(updater.update_is_stuck({"state": "downloading", "at": 800}, 1_000))
        self.assertFalse(updater.update_is_stuck({"state": "idle"}, 1_000))

    def test_start_answers_before_asking_github(self):
        with unittest.mock.patch.object(updater, "status", return_value={"state": "idle"}), \
             unittest.mock.patch.object(updater, "_update_lock") as lock, \
             unittest.mock.patch.object(updater, "write"), \
             unittest.mock.patch.object(updater, "current_version", return_value="0.1.10"), \
             unittest.mock.patch.object(updater, "api", side_effect=AssertionError("GitHub should not be called yet")), \
             unittest.mock.patch.object(updater.threading, "Thread") as thread:
            lock.acquire.return_value = True
            self.assertEqual(updater.start(), "started")
            updater.api.assert_not_called()
            thread.return_value.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
