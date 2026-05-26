import unittest
from unittest.mock import MagicMock, patch

import requests

from app.services.sora2.base import Sora2TaskStatus
from app.services.sora2.xiaobanshou import Sora2Xiaobanshou


class Sora2XiaobanshouTests(unittest.TestCase):
    @patch("app.services.sora2.xiaobanshou.requests.post")
    def test_text_create_uses_json_contract_from_docs(self, mock_post):
        service = Sora2Xiaobanshou("test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id":"task_xbs_123","status":"pending","progress":0}'
        mock_response.json.return_value = {
            "id": "task_xbs_123",
            "status": "pending",
            "progress": 0,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = service.create_task("a cat in a garden")

        self.assertEqual(result.task_id, "task_xbs_123")
        self.assertEqual(result.status, Sora2TaskStatus.PENDING)

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["json"]["model"], "sora-2-portrait-10s")
        self.assertEqual(kwargs["json"]["prompt"], "a cat in a garden")

    @patch("app.services.sora2.xiaobanshou.requests.post")
    def test_text_create_parses_live_success_shape(self, mock_post):
        service = Sora2Xiaobanshou("test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '{"id":"task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ","task_id":"task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ",'
            '"object":"video","model":"sora2-landscape-10s","status":"queued","progress":0,"created_at":1774004442,"size":"720x720"}'
        )
        mock_response.json.return_value = {
            "id": "task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ",
            "task_id": "task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ",
            "object": "video",
            "model": "sora2-landscape-10s",
            "status": "queued",
            "progress": 0,
            "created_at": 1774004442,
            "size": "720x720",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = service.create_task("a cat in a garden")

        self.assertEqual(result.task_id, "task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ")
        self.assertEqual(result.status, Sora2TaskStatus.PENDING)
        self.assertEqual(result.progress, 0)
        self.assertEqual(result.created_at, "1774004442")

    @patch("app.services.sora2.xiaobanshou.requests.post")
    def test_text_create_extracts_real_unauthorized_error_shape(self, mock_post):
        service = Sora2Xiaobanshou("test-key")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = (
            '{"error":{"code":"","message":"无效的令牌 '
            '(request id: 20260320105735190212647lYtLKDZK)","type":"new_api_error"}}'
        )
        mock_response.json.return_value = {
            "error": {
                "code": "",
                "message": "无效的令牌 (request id: 20260320105735190212647lYtLKDZK)",
                "type": "new_api_error",
            }
        }
        http_error = requests.exceptions.HTTPError("401 Client Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        result = service.create_task("a cat in a garden")

        self.assertEqual(result.status, Sora2TaskStatus.FAILED)
        self.assertIn("无效的令牌", result.error_message)

    @patch("app.services.sora2.xiaobanshou.requests.get")
    def test_query_task_parses_live_completed_shape(self, mock_get):
        service = Sora2Xiaobanshou("test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '{"id":"task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ","size":"720x720","model":"sora2-landscape-10s",'
            '"object":"video","status":"completed","video_url":"https://us1.ss5.life/example.mp4",'
            '"created_at":1774004442,"completed_at":1774004604}'
        )
        mock_response.json.return_value = {
            "id": "task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ",
            "size": "720x720",
            "model": "sora2-landscape-10s",
            "object": "video",
            "status": "completed",
            "video_url": "https://us1.ss5.life/example.mp4",
            "created_at": 1774004442,
            "completed_at": 1774004604,
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = service.query_task("task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ")

        self.assertEqual(result.task_id, "task_Vzc8ezUuftzGMOtQ7uy55cK491xIvxrJ")
        self.assertEqual(result.status, Sora2TaskStatus.COMPLETED)
        self.assertEqual(result.video_url, "https://us1.ss5.life/example.mp4")
        self.assertEqual(result.created_at, "1774004442")
        self.assertEqual(result.completed_at, "1774004604")

    @patch("app.services.sora2.xiaobanshou.requests.get")
    def test_query_task_keeps_polling_on_connection_reset(self, mock_get):
        service = Sora2Xiaobanshou("test-key")

        mock_get.side_effect = requests.exceptions.ConnectionError(
            "('Connection aborted.', ConnectionResetError(10054, '远程主机强迫关闭了一个现有的连接。', None, 10054, None))"
        )

        result = service.query_task("task_xbs_123")

        self.assertEqual(result.task_id, "task_xbs_123")
        self.assertEqual(result.status, Sora2TaskStatus.PROCESSING)
        self.assertIn("Connection aborted", result.error_message)

    @patch("app.services.sora2.xiaobanshou.requests.get")
    def test_get_video_content_parses_live_binary_download(self, mock_get):
        service = Sora2Xiaobanshou("test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake-mp4-bytes"
        mock_response.headers = {"Content-Type": "video/mp4"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value.__enter__.return_value = mock_response
        mock_get.return_value.__exit__.return_value = None

        data, content_type, error_message = service.get_video_content("task_xbs_123")

        self.assertEqual(data, b"fake-mp4-bytes")
        self.assertEqual(content_type, "video/mp4")
        self.assertIsNone(error_message)

if __name__ == "__main__":
    unittest.main()
