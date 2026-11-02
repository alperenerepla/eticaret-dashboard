"""Kaynak SQLite'ın değişmediğini ve temel metriklerin beklenen gibi hesaplandığını denetler."""
from pathlib import Path
import sqlite3

DB = Path(__file__).with_name('eticaret.sqlite')
con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
expected = {'siparisler':8044,'siparis_kalemleri':13858,'olaylar':105136,'musteriler':2100,'urunler':131,'iadeler':667}
for table, n in expected.items():
    actual = con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    assert actual == n, f'{table}: {actual} != {n}'
assert con.execute("SELECT COUNT(*) FROM siparisler WHERE durum='teslim_edildi'").fetchone()[0] == 7644
assert not con.execute('PRAGMA foreign_key_check').fetchall()
assert con.execute('SELECT COUNT(*) FROM siparisler WHERE ABS(ara_toplam-kupon_indirimi+kargo_ucreti-toplam_tutar) > 0.05').fetchone()[0] == 0
assert con.execute('SELECT COUNT(*) FROM siparis_kalemleri WHERE ABS(adet*birim_satis_fiyati-kalem_tutari) > 0.05').fetchone()[0] == 0
q = '''WITH r AS (SELECT siparis_id, sum(iade_tutari) AS refund FROM iadeler WHERE durum='tamamlandi' GROUP BY siparis_id)
SELECT ROUND(SUM(s.ara_toplam - s.kupon_indirimi - COALESCE(r.refund,0)),2)
FROM siparisler AS s LEFT JOIN r ON r.siparis_id=s.siparis_id WHERE s.durum='teslim_edildi' '''
net = con.execute(q).fetchone()[0]
assert abs(net - 24588466.13)<0.01, f'Unexpected net product sales: {net}'
print('Tüm veri bütünlüğü kontrolleri başarılı.')
print('Teslim edilmiş sipariş sayısı: 7644')
print('Tamamlanan iadeler düşülmüş net ürün satışı (kargo hariç): 24.588.466,13 TL')
