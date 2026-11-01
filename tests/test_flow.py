import asyncio
import os
import unittest
from app.registry import registry
from app.parser import parser
from app.storage import storage
from app.task_engine import task_engine
from app.models import TaskStatus

class TestVolunteerFlow(unittest.TestCase):
    def setUp(self):
        # Force mock mode during all tests
        from app.config import settings
        from app.whatsapp_service import whatsapp_service
        settings.WHATSAPP_PROVIDER = "mock"
        whatsapp_service.provider = "mock"
        registry.load()

    def test_volunteer_resolution(self):
        # 1. Exact handle match
        vol, conf = registry.resolve("Faith")
        self.assertIsNotNone(vol)
        self.assertIn("Faith Wanjiru", vol.name)
        self.assertGreaterEqual(conf, 0.9)

        # 2. Tag with @ sign
        vol, conf = registry.resolve("@Brian")
        self.assertIsNotNone(vol)
        self.assertEqual(vol.name, "Brian Kithusi")

        # 3. Fuzzy partial name match
        vol, conf = registry.resolve("derrick")
        self.assertIsNotNone(vol)
        self.assertIn("Derrick Omwanza", vol.name)

    def test_trigger_detection(self):
        self.assertTrue(parser.has_trigger("@task @Faith please check 3d printer"))
        self.assertTrue(parser.has_trigger("Team, please remember @task @Brian help with chess"))
        self.assertTrue(parser.has_trigger("@task Nicole draft the flyer"))
        self.assertFalse(parser.has_trigger("Hello everyone, how was the weekend?"))

    def test_end_to_end_assignment_and_volunteer_reply(self):
        async def run_flow():
            # 1. Coordinator assigns task in group
            coord_message = "@task @Faith please inspect the Makerbot 3D printer wiring by tomorrow 3pm"
            result = await task_engine.process_group_message(
                sender_name="Coordinator (Ryan)",
                sender_phone="+254700000000",
                text=coord_message,
                chat_id="mtaani_group@g.us"
            )

            self.assertTrue(result["is_task"])
            self.assertEqual(result["status"], "ASSIGNED")
            self.assertIn("Faith Wanjiru", result["volunteer"]["name"])
            task_id = result["task"]["id"]

            # Verify saved in storage
            saved_task = storage.get_task(task_id)
            self.assertIsNotNone(saved_task)
            self.assertEqual(saved_task.status, TaskStatus.DM_SENT)

            # 2. Volunteer replies "1" to accept via private DM
            vol_phone = result["volunteer"]["phone"]
            reply_res = await task_engine.process_volunteer_message(
                sender_phone=vol_phone,
                sender_name="Faith Wanjiru",
                text="1"
            )
            self.assertEqual(reply_res["status"], "ACKNOWLEDGED")
            updated_task = storage.get_task(task_id)
            self.assertEqual(updated_task.status, TaskStatus.ACKNOWLEDGED)

            # 3. Volunteer replies "Done" when completed
            done_res = await task_engine.process_volunteer_message(
                sender_phone=vol_phone,
                sender_name="Faith Wanjiru",
                text="Done! Everything printed smoothly."
            )
            self.assertEqual(done_res["status"], "COMPLETED")
            completed_task = storage.get_task(task_id)
            self.assertEqual(completed_task.status, TaskStatus.COMPLETED)

        asyncio.run(run_flow())

if __name__ == "__main__":
    unittest.main()
