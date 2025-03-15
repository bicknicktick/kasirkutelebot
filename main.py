from database import tambah_produk_sample
from telegram_bot import main

if __name__ == "__main__":
    # Tambahkan produk sampel ke database
    tambah_produk_sample()
    
    # Jalankan bot Telegram
    main() 