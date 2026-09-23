# API integration tests สำหรับ node endpoints
# ใช้ fake Netmiko จาก conftest — ไม่ต้องเชื่อมต่ออุปกรณ์จริง

from __future__ import annotations

from backend.tests.conftest import SERIAL_NODE_PAYLOAD, SSH_NODE_PAYLOAD, TELNET_NODE_PAYLOAD


class TestCreateNode:
    """ทดสอบ POST /nodes"""

    def test_create_ssh_node_success(self, client):
        """สร้าง SSH node — response ต้องไม่มี password/secret"""
        resp = client.post("/nodes", json=SSH_NODE_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["hostname"] == "R1"
        assert data["transport"] == "ssh"
        assert "password" not in data
        assert "secret" not in data
        assert "enc_password" not in data
        assert "id" in data
        assert "created_at" in data
        assert data["status"] == "connected"

    def test_create_telnet_node_success(self, client):
        """สร้าง Telnet node"""
        resp = client.post("/nodes", json=TELNET_NODE_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["transport"] == "telnet"

    def test_create_telnet_password_only_success(self, client):
        """Telnet แบบถามเฉพาะ password ต้องสร้างได้โดยไม่ส่ง username"""
        payload = {
            **TELNET_NODE_PAYLOAD,
            "hostname": "R2_password_only",
            "transport_config": {
                **TELNET_NODE_PAYLOAD["transport_config"],
                "host": "192.168.1.22",
            },
        }
        payload["transport_config"].pop("username")
        resp = client.post("/nodes", json=payload)
        assert resp.status_code == 201
        assert resp.json()["transport"] == "telnet"

    def test_create_serial_node_success(self, client):
        """สร้าง Serial node — host/port เป็น None"""
        resp = client.post("/nodes", json=SERIAL_NODE_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["transport"] == "serial"
        assert data["serial_port"] == "COM3"

    def test_create_serial_without_credentials_success(self, client):
        """Serial console ที่ไม่ถาม username/password ต้องสร้างได้"""
        payload = {
            **SERIAL_NODE_PAYLOAD,
            "hostname": "R3_console_only",
            "transport_config": {
                "transport": "serial",
                "serial_port": "COM4",
                "baudrate": 9600,
            },
        }
        resp = client.post("/nodes", json=payload)
        assert resp.status_code == 201
        assert resp.json()["transport"] == "serial"

    def test_create_duplicate_ssh_node_returns_409(self, client):
        """สร้าง node ซ้ำ (host+port+transport) ต้องได้ 409"""
        payload = {**SSH_NODE_PAYLOAD, "hostname": "R1_dup"}
        resp = client.post("/nodes", json=payload)
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "DUPLICATE_NODE"

    def test_create_node_invalid_ip_returns_422(self, client):
        """IP ไม่ถูกต้องต้อง fail validation และ return 422"""
        bad = {
            "hostname": "Bad",
            "transport_config": {
                "transport": "ssh",
                "host": "999.999.999.999",
                "port": 22,
                "username": "admin",
                "password": "cisco",
            },
        }
        resp = client.post("/nodes", json=bad)
        assert resp.status_code == 422

    def test_create_node_missing_password_returns_422(self, client):
        """ไม่มี password ต้อง fail validation"""
        bad = {
            "hostname": "Bad2",
            "transport_config": {
                "transport": "ssh",
                "host": "192.168.1.99",
                "port": 22,
                "username": "admin",
            },
        }
        resp = client.post("/nodes", json=bad)
        assert resp.status_code == 422


class TestListNodes:
    """ทดสอบ GET /nodes"""

    def test_list_nodes_returns_array(self, client):
        """GET /nodes ต้องคืน list และ total"""
        resp = client.get("/nodes")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "total" in data
        assert isinstance(data["nodes"], list)

    def test_list_nodes_no_credentials(self, client):
        """nodes ใน list ต้องไม่มี credential"""
        resp = client.get("/nodes")
        for node in resp.json()["nodes"]:
            assert "password" not in node
            assert "secret" not in node
            assert "enc_password" not in node

    def test_search_by_hostname(self, client):
        """ค้นหาด้วย hostname ต้องกรองได้"""
        resp = client.get("/nodes?q=R1")
        assert resp.status_code == 200
        nodes = resp.json()["nodes"]
        # ควรมี R1 อยู่ในผล
        hostnames = [n["hostname"] for n in nodes]
        assert any("R1" in h for h in hostnames)


class TestGetNode:
    """ทดสอบ GET /nodes/{id}"""

    def test_get_node_not_found_returns_404(self, client):
        """Node ที่ไม่มีต้องได้ 404 พร้อม error code ไทย"""
        resp = client.get("/nodes/nonexistent-id")
        assert resp.status_code == 404
        data = resp.json()
        # FastAPI คืน detail dict
        detail = data.get("detail", data)
        assert detail.get("code") == "NODE_NOT_FOUND"


class TestDeleteNode:
    """ทดสอบ DELETE /nodes/{id}"""

    def test_delete_node_success(self, client):
        """ลบ node ที่มีอยู่ต้องได้ 204"""
        # สร้าง node ที่จะลบ
        unique_payload = {
            "hostname": "ToDelete",
            "transport_config": {
                "transport": "ssh",
                "host": "10.0.0.1",
                "port": 22,
                "username": "admin",
                "password": "pass123",
            },
        }
        create_resp = client.post("/nodes", json=unique_payload)
        node_id = create_resp.json()["id"]

        del_resp = client.delete(f"/nodes/{node_id}")
        assert del_resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, client):
        """ลบ node ที่ไม่มีต้องได้ 404"""
        resp = client.delete("/nodes/fake-uuid-that-does-not-exist")
        assert resp.status_code == 404


class TestTestNodeConnection:
    """ทดสอบ POST /nodes/{id}/test"""

    def test_draft_test_success_does_not_persist_node(
        self, client, fake_ping_success, fake_port_open, fake_netmiko_success
    ):
        """ทดสอบก่อนบันทึกผ่าน — ต้องคืนผลสำเร็จแต่ไม่สร้าง row ใน DB"""
        payload = {
            **SSH_NODE_PAYLOAD,
            "hostname": "DraftSuccess",
            "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "192.0.2.10"},
        }
        resp = client.post("/nodes/test", json=payload)
        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "success"
        assert client.get("/nodes?q=DraftSuccess").json()["total"] == 0

    def test_draft_test_failure_does_not_persist_node(self, client, fake_ping_success, fake_port_closed):
        """ทดสอบก่อนบันทึกล้มเหลว — ต้องไม่สร้าง node ที่ unreachable"""
        payload = {
            **SSH_NODE_PAYLOAD,
            "hostname": "DraftFailure",
            "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "192.0.2.11"},
        }
        resp = client.post("/nodes/test", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "failed"
        port_step = next(step for step in data["steps"] if step["step"] == "port")
        assert port_step["status"] == "failed"
        assert client.get("/nodes?q=DraftFailure").json()["total"] == 0

    def _get_first_ssh_node_id(self, client) -> str:
        """Helper: คืน ID ของ SSH node แรกใน list"""
        resp = client.get("/nodes?q=R1")
        nodes = resp.json()["nodes"]
        ssh_nodes = [n for n in nodes if n["transport"] == "ssh" and n["hostname"] == "R1"]
        assert ssh_nodes, "ต้องมี R1 SSH node อยู่ใน DB (จาก test_create_ssh_node)"
        return ssh_nodes[0]["id"]

    def test_test_connection_success(
        self, client, fake_ping_success, fake_port_open, fake_netmiko_success
    ):
        """ทดสอบ connection สำเร็จโดยไม่ต้องใช้ enable secret"""
        node_id = self._get_first_ssh_node_id(client)
        resp = client.post(f"/nodes/{node_id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "success"
        assert data["hostname_detected"] == "R1"
        node = client.get(f"/nodes/{node_id}").json()
        assert node["status"] == "connected"
        step_names = [s["step"] for s in data["steps"]]
        assert "ping" in step_names
        assert "login" in step_names
        fake_netmiko_success.return_value.enable.assert_not_called()

    def test_test_connection_ping_fail(self, client, fake_ping_fail):
        """ping ล้มเหลว — ต้องได้ FAILED และ skip ขั้นถัดไป"""
        node_id = self._get_first_ssh_node_id(client)
        resp = client.post(f"/nodes/{node_id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "failed"
        node = client.get(f"/nodes/{node_id}").json()
        assert node["status"] == "unreachable"
        ping_step = next(s for s in data["steps"] if s["step"] == "ping")
        assert ping_step["status"] == "failed"
        # ขั้นหลังต้อง skip
        skipped = [s for s in data["steps"] if s["status"] == "skipped"]
        assert len(skipped) >= 2

    def test_test_connection_auth_fail(
        self, client, fake_ping_success, fake_port_open, fake_netmiko_auth_fail
    ):
        """auth ล้มเหลว — ต้องได้ FAILED และ message ไทย ไม่มี traceback"""
        node_id = self._get_first_ssh_node_id(client)
        resp = client.post(f"/nodes/{node_id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "failed"
        login_step = next(s for s in data["steps"] if s["step"] == "login")
        assert login_step["status"] == "failed"
        # message ต้องไม่มี traceback หรือ exception class
        assert "Traceback" not in login_step["message"]
        assert "Exception" not in login_step["message"]

    def test_ssh_connection_uses_ios_compatible_timeouts(
        self, client, fake_ping_success, fake_port_open, fake_netmiko_success
    ):
        """SSH draft test ต้องเผื่อ banner/auth prompt ของ IOSv และไม่ใช้ fast_cli"""
        payload = {
            **SSH_NODE_PAYLOAD,
            "hostname": "SlowIOS",
            "transport_config": {**SSH_NODE_PAYLOAD["transport_config"], "host": "192.0.2.20"},
        }
        response = client.post("/nodes/test", json=payload)
        assert response.status_code == 200
        kwargs = fake_netmiko_success.call_args.kwargs
        assert kwargs["auth_timeout"] == 30
        assert kwargs["banner_timeout"] == 30
        assert kwargs["read_timeout_override"] == 30
        assert kwargs["fast_cli"] is False

    def test_test_nonexistent_node_returns_404(self, client):
        """Test node ที่ไม่มีต้องได้ 404"""
        resp = client.post("/nodes/nonexistent-id/test")
        assert resp.status_code == 404
