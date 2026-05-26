import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

from app.services.sora2.bandianwa import Sora2Bandianwa
from app.services.sora2.base import Sora2TaskStatus


class Sora2BandianwaTests(unittest.TestCase):
    def setUp(self):
        self.service = Sora2Bandianwa("test-key")

    def test_infer_seconds_from_model(self):
        self.assertEqual(self.service._infer_seconds_from_model("sora-2-portrait-10s-guanzhuan"), 10)
        self.assertEqual(self.service._infer_seconds_from_model("sora-2-landscape-15s-guanzhuan"), 15)
        self.assertIsNone(self.service._infer_seconds_from_model("invalid-model"))

    @patch("app.services.sora2.bandianwa.requests.post")
    def test_create_task_image_uses_multipart_contract(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id":"task_123","status":"pending","progress":0}'
        mock_response.json.return_value = {
            "id": "task_123",
            "status": "pending",
            "progress": 0,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"fake-image")
            tmp.flush()

            result = self.service.create_task(
                "make a video",
                model="sora-2-portrait-10s-guanzhuan",
                image_path=tmp.name,
                size="720p",
            )

        self.assertEqual(result.task_id, "task_123")
        self.assertEqual(result.status, Sora2TaskStatus.PENDING)

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["data"]["model"], "sora-2-portrait-10s-guanzhuan")
        self.assertEqual(kwargs["data"]["prompt"], "make a video")
        self.assertEqual(kwargs["data"]["seconds"], "10")
        self.assertEqual(kwargs["data"]["size"], "720p")
        self.assertEqual(kwargs["data"]["n"], "1")
        self.assertIn("input_reference", kwargs["files"])

    @patch("app.services.sora2.bandianwa.requests.post")
    def test_create_task_image_extracts_real_unauthorized_error_shape(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = (
            '{"error":{"code":"","message":"无效的令牌 '
            '(request id: 2026032010441495667443wozGSNp3)","type":"new_api_error"}}'
        )
        mock_response.json.return_value = {
            "error": {
                "code": "",
                "message": "无效的令牌 (request id: 2026032010441495667443wozGSNp3)",
                "type": "new_api_error",
            }
        }
        http_error = requests.exceptions.HTTPError("401 Client Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"fake-image")
            tmp.flush()
            result = self.service.create_task(
                "make a video",
                model="sora-2-portrait-10s-guanzhuan",
                image_path=tmp.name,
                size="720p",
            )

        self.assertEqual(result.status, Sora2TaskStatus.FAILED)
        self.assertIn("无效的令牌", result.error_message)

    @patch("app.services.sora2.dayangyu.requests.get")
    def test_query_task_extracts_real_unauthorized_error_shape(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = (
            '{"error":{"code":"","message":"无效的令牌 '
            '(request id: 20260320104137570708524gIFGW8yc)","type":"new_api_error"}}'
        )
        mock_response.json.return_value = {
            "error": {
                "code": "",
                "message": "无效的令牌 (request id: 20260320104137570708524gIFGW8yc)",
                "type": "new_api_error",
            }
        }
        http_error = requests.exceptions.HTTPError("401 Client Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        result = self.service.query_task("test_task_id")

        self.assertEqual(result.status, Sora2TaskStatus.FAILED)
        self.assertIn("无效的令牌", result.error_message)

    @patch("app.services.sora2.dayangyu.requests.get")
    def test_query_task_keeps_polling_on_connection_reset(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "('Connection aborted.', ConnectionResetError(10054, '远程主机强迫关闭了一个现有的连接。', None, 10054, None))"
        )

        result = self.service.query_task("test_task_id")

        self.assertEqual(result.task_id, "test_task_id")
        self.assertEqual(result.status, Sora2TaskStatus.PROCESSING)
        self.assertIn("Connection aborted", result.error_message)

    @patch("app.services.sora2.dayangyu.requests.get")
    def test_get_video_content_extracts_real_unauthorized_error_shape(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = (
            '{"error":{"code":"","message":"无效的令牌 '
            '(request id: 20260320104137572713999Hu5AFQGi)","type":"new_api_error"}}'
        )
        mock_response.json.return_value = {
            "error": {
                "code": "",
                "message": "无效的令牌 (request id: 20260320104137572713999Hu5AFQGi)",
                "type": "new_api_error",
            }
        }
        http_error = requests.exceptions.HTTPError("401 Client Error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value.__enter__.return_value = mock_response
        mock_get.return_value.__exit__.return_value = None

        data, content_type, error_message = self.service.get_video_content("test_task_id")

        self.assertIsNone(data)
        self.assertIsNone(content_type)
        self.assertIn("无效的令牌", error_message)


if __name__ == "__main__":
    unittest.main()
