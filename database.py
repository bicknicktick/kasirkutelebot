from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class Produk(Base):
    __tablename__ = 'produk'
    
    id = Column(Integer, primary_key=True)
    nama = Column(String, nullable=False)
    harga = Column(Float, nullable=False)
    stok = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Produk(nama='{self.nama}', harga={self.harga}, stok={self.stok})>"

class Pelanggan(Base):
    __tablename__ = 'pelanggan'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    nama = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<Pelanggan(nama='{self.nama}', telegram_id='{self.telegram_id}')>"

class Transaksi(Base):
    __tablename__ = 'transaksi'
    
    id = Column(Integer, primary_key=True)
    pelanggan_id = Column(Integer, ForeignKey('pelanggan.id'))
    total = Column(Float, default=0)
    tanggal = Column(String)
    
    pelanggan = relationship("Pelanggan")
    items = relationship("TransaksiItem", back_populates="transaksi")
    
    def __repr__(self):
        return f"<Transaksi(id={self.id}, total={self.total})>"

class TransaksiItem(Base):
    __tablename__ = 'transaksi_item'
    
    id = Column(Integer, primary_key=True)
    transaksi_id = Column(Integer, ForeignKey('transaksi.id'))
    produk_id = Column(Integer, ForeignKey('produk.id'))
    jumlah = Column(Integer)
    harga_satuan = Column(Float)
    
    transaksi = relationship("Transaksi", back_populates="items")
    produk = relationship("Produk")
    
    def __repr__(self):
        return f"<TransaksiItem(produk_id={self.produk_id}, jumlah={self.jumlah})>"

# Inisialisasi database
engine = create_engine('sqlite:///kasir.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

# Fungsi untuk menambahkan produk sample
def tambah_produk_sample():
    session = get_session()
    
    # Cek apakah sudah ada produk
    produk_count = session.query(Produk).count()
    if produk_count == 0:
        produk_sample = [
            Produk(nama="Kopi Hitam", harga=10000, stok=100),
            Produk(nama="Teh Manis", harga=8000, stok=100),
            Produk(nama="Roti Bakar", harga=15000, stok=50),
            Produk(nama="Nasi Goreng", harga=25000, stok=30),
            Produk(nama="Air Mineral", harga=5000, stok=200)
        ]
        
        session.add_all(produk_sample)
        session.commit()
    
    session.close() 