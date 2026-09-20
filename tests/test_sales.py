import unittest
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from everyday.sales import transactions, render, demo
from everyday.common import packet


class SalesTests(unittest.TestCase):
    def test_money_duplicates_refunds_currency_and_local_month(self):
        now = datetime(2026, 9, 20, 12, tzinfo=ZoneInfo("Europe/Prague"))
        csv = "id,date,product,type,licenses,amount,currency\n" + "\n".join([
            "1,2026-08-31T23:00:00Z,Tool,NEW,2,0.10,EUR",
            "2,2026-09-02,Tool,RENEW,1,0.20,EUR",
            "2,2026-09-02,Tool,RENEW,1,0.20,EUR",
            "3,2026-09-03,Tool,REFUND,1,0.10,EUR",
            "4,2026-09-04,Other,NEW,1,999,USD",
            "5,2026-10-01,Tool,NEW,1,999,EUR"])
        rows = list(transactions(csv, {}, now))
        self.assertEqual(rows[2]["amount"], Decimal("-0.10"))
        result = render(rows, {"currency": "EUR"}, now, source="CSV")
        self.assertEqual(result["hero"], "0.20")
        self.assertEqual([m["value"] for m in result["metrics"]], ["2", "1", "0.10"])
        self.assertIn("1 other-currency", result["source"])
        self.assertLessEqual(len(packet(demo(now))), 2000)
        with self.assertRaises(ValueError):
            list(transactions(csv + "\n1,2026-09-01,Tool,NEW,3,0.10,EUR", {}, now))
        with self.assertRaises(ValueError):
            list(transactions(csv.replace("0.20", "NaN"), {}, now))

    def test_column_mapping(self):
        now = datetime(2026, 9, 20, tzinfo=ZoneInfo("Europe/Prague"))
        config = {"delimiter": ";", "date_format": "%d.%m.%Y", "columns": {"id": "Ref", "date": "Day"},
                  "types": {"PURCHASE": "new"}}
        row = list(transactions("Ref;Day;product;type;licenses;amount;currency\na;01.09.2026;Tool;PURCHASE;1;19.90;EUR", config, now))[0]
        self.assertEqual(row["kind"], "new")
        self.assertEqual(row["when"].month, 9)


if __name__ == "__main__":
    unittest.main()
