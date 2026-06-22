import csv
import tempfile
import os
from datetime import date
from app.ingestion.csv_parsers.hdfc import HdfcCsvParser
from app.ingestion.csv_parsers.generic import GenericCsvParser
from app.ingestion.registry import get_parser
from app.utils.dedup import file_hash, row_hash
from app.utils.transfers import is_internal_transfer


def make_hdfc_csv(tmp_path: str) -> str:
    path = os.path.join(tmp_path, "hdfc.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"])
        w.writerow(["01/05/25", "ZOMATO ORDER", "", "", "350.00", "", "10000"])
        w.writerow(["02/05/25", "SALARY CREDIT", "", "", "", "50000.00", "60000"])
        w.writerow(["03/05/25", "UBER RIDE", "", "", "120.00", "", "59880"])
    return path


def make_generic_csv(tmp_path: str) -> str:
    path = os.path.join(tmp_path, "generic.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Amount"])
        w.writerow(["01/05/2025", "Coffee Shop", "150.00"])
        w.writerow(["02/05/2025", "Netflix", "649.00"])
    return path


def test_hdfc_parser_identifies_file():
    parser = HdfcCsvParser()
    headers = ["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"]
    assert parser.can_parse("any.csv", headers) is True


def test_hdfc_parser_rejects_unknown_headers():
    parser = HdfcCsvParser()
    assert parser.can_parse("any.csv", ["Date", "Amount", "Description"]) is False


def test_hdfc_parser_parses_transactions():
    with tempfile.TemporaryDirectory() as tmp:
        path = make_hdfc_csv(tmp)
        parser = HdfcCsvParser()
        txns = parser.parse(path)
        assert len(txns) == 3
        debits = [t for t in txns if t.transaction_type == "debit"]
        credits = [t for t in txns if t.transaction_type == "credit"]
        assert len(debits) == 2
        assert len(credits) == 1
        assert debits[0].amount == 350.0
        assert debits[0].description == "ZOMATO ORDER"
        assert debits[0].date == date(2025, 5, 1)


def test_registry_selects_hdfc_parser():
    with tempfile.TemporaryDirectory() as tmp:
        path = make_hdfc_csv(tmp)
        parser = get_parser(path)
        assert parser.SOURCE_NAME == "hdfc_csv"


def test_registry_falls_back_to_generic():
    with tempfile.TemporaryDirectory() as tmp:
        path = make_generic_csv(tmp)
        parser = get_parser(path)
        assert parser.SOURCE_NAME == "generic_csv"


def test_generic_parser_parses_amount_column():
    with tempfile.TemporaryDirectory() as tmp:
        path = make_generic_csv(tmp)
        parser = GenericCsvParser()
        txns = parser.parse(path)
        assert len(txns) == 2
        assert txns[0].amount == 150.0


def test_file_hash_is_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        path = make_hdfc_csv(tmp)
        h1 = file_hash(path)
        h2 = file_hash(path)
        assert h1 == h2
        assert len(h1) == 64


def test_row_hash_is_deterministic():
    h1 = row_hash("2025-05-01", 350.0, "ZOMATO ORDER")
    h2 = row_hash("2025-05-01", 350.0, "ZOMATO ORDER")
    assert h1 == h2
    assert len(h1) == 64


def test_row_hash_differs_for_different_data():
    h1 = row_hash("2025-05-01", 350.0, "ZOMATO ORDER")
    h2 = row_hash("2025-05-01", 350.0, "SWIGGY ORDER")
    assert h1 != h2


def test_row_hash_differs_across_accounts():
    # Same date/amount/description in two different accounts must NOT collide,
    # otherwise one account's transaction silently eats the other's.
    h_acct1 = row_hash("2025-05-01", 200.0, "SWIGGY ORDER", account_id=1)
    h_acct2 = row_hash("2025-05-01", 200.0, "SWIGGY ORDER", account_id=2)
    assert h_acct1 != h_acct2


def test_row_hash_same_account_still_dedups():
    h1 = row_hash("2025-05-01", 200.0, "SWIGGY ORDER", account_id=1)
    h2 = row_hash("2025-05-01", 200.0, "SWIGGY ORDER", account_id=1)
    assert h1 == h2


NAMES = ["YOURNAME"]


def test_detects_self_imps_transfer():
    desc = "IMPS-000000000000-YOURNAME-UTIB-XXXXXXXXXXX0000-IM"
    assert is_internal_transfer(desc, NAMES) is True


def test_does_not_flag_investment_return_to_self():
    # name appears only as a truncated beneficiary, sender is EXAMPLE CORP — real income
    desc = "NEFT CR-XXXX0000000-EXAMPLE CORP NOV 2025-YOURNAM"
    assert is_internal_transfer(desc, NAMES) is False


def test_does_not_flag_salary_or_merchants():
    assert is_internal_transfer("SALARY CREDIT", NAMES) is False
    assert is_internal_transfer("UPI-SWIGGY-SWIGGYSTORES@ICICI", NAMES) is False


def test_no_names_configured_flags_nothing():
    assert is_internal_transfer("IMPS-123-YOURNAME-UTIB", []) is False


from app.utils.merchant import normalize_merchant


def test_merchant_strips_reference_numbers():
    # same payee, different per-txn reference -> same merchant key
    a = normalize_merchant("ACH D- INDIAN CLEARING CORP-P7173384X179")
    b = normalize_merchant("ACH D- INDIAN CLEARING CORP-P7173384X185")
    assert a == b == "INDIAN CLEARING CORP"


def test_merchant_extracts_upi_payee():
    d = "UPI-CRED CLUB-CRED.CLUB@AXISB-UTIB0000114-645902607640-PAYMENT ON CRED"
    assert normalize_merchant(d) == "CRED CLUB"


def test_merchant_skips_ifsc_and_takes_name():
    d = "NEFT DR-PUNB0296800-SUBHASH KUMAR SINGH-NETBANK, MUM-HDFCH00911191177-APR26"
    assert normalize_merchant(d) == "SUBHASH KUMAR SINGH"


def test_merchant_drops_trailing_note_noise():
    # payee field present; trailing "PAID VIA CRED" must not win
    d = "UPI-HARI SINGH-PAYTM.S1TRCRY@PTY-YESB0MCHUPI-648015132598-PAID VIA CRED"
    assert normalize_merchant(d) == "HARI SINGH"
