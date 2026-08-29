from django.test import TestCase
from django.urls import resolve, reverse

from apps.demo_one.services.data import DemoOneDataService


class DemoOneTests(TestCase):
    def test_index_returns_200(self):
        response = self.client.get(reverse("demo_one:index"))
        self.assertEqual(response.status_code, 200)

    def test_service_returns_items(self):
        items = DemoOneDataService.list_items()
        self.assertEqual(len(items), 3)
        self.assertIn("name", items[0])
        self.assertIn("status", items[0])

    def test_url_namespace(self):
        self.assertEqual(reverse("demo_one:index"), "/apps/demo-one/")
        self.assertEqual(resolve("/apps/demo-one/").view_name, "demo_one:index")
