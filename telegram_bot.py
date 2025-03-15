from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
import logging
from datetime import datetime

from database import get_session, Produk, Pelanggan, Transaksi, TransaksiItem

# Mengatur logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Menyimpan keranjang belanja pengguna
keranjang = {}

def start(update: Update, context: CallbackContext) -> None:
    """Mengirim pesan saat perintah /start diterima."""
    user = update.effective_user
    
    # Daftarkan pengguna jika belum terdaftar
    session = get_session()
    pelanggan = session.query(Pelanggan).filter_by(telegram_id=str(user.id)).first()
    
    if not pelanggan:
        pelanggan = Pelanggan(telegram_id=str(user.id), nama=user.first_name)
        session.add(pelanggan)
        session.commit()
    
    session.close()
    
    update.message.reply_text(
        f'Halo {user.first_name}! Selamat datang di Bot Kasir.\n'
        'Gunakan /produk untuk melihat daftar produk yang tersedia.\n'
        'Gunakan /keranjang untuk melihat keranjang belanja Anda.\n'
        'Gunakan /checkout untuk menyelesaikan pembelian.'
    )

def produk(update: Update, context: CallbackContext) -> None:
    """Menampilkan daftar produk yang tersedia."""
    session = get_session()
    produk_list = session.query(Produk).all()
    session.close()
    
    if not produk_list:
        update.message.reply_text('Tidak ada produk yang tersedia.')
        return
    
    keyboard = []
    for produk in produk_list:
        keyboard.append([
            InlineKeyboardButton(
                f"{produk.nama} - Rp {produk.harga:,.0f} (Stok: {produk.stok})",
                callback_data=f"beli_{produk.id}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Pilih produk untuk dibeli:', reply_markup=reply_markup)

def handle_button(update: Update, context: CallbackContext) -> None:
    """Menangani ketika tombol inline ditekan."""
    query = update.callback_query
    query.answer()
    
    # Ambil data dari callback
    data = query.data
    
    if data.startswith('beli_'):
        produk_id = int(data.split('_')[1])
        tambah_ke_keranjang(update, context, produk_id)
    elif data.startswith('hapus_'):
        produk_id = data.split('_')[1]
        hapus_dari_keranjang(update, context, produk_id)
    elif data == "checkout":
        checkout(update, context)
    elif data == "kosongkan":
        kosongkan_keranjang(update, context)

def tambah_ke_keranjang(update: Update, context: CallbackContext, produk_id: int) -> None:
    """Menambahkan produk ke keranjang belanja."""
    user_id = str(update.effective_user.id)
    
    # Inisialisasi keranjang pengguna jika belum ada
    if user_id not in keranjang:
        keranjang[user_id] = {}
    
    # Ambil informasi produk
    session = get_session()
    produk = session.query(Produk).get(produk_id)
    session.close()
    
    if not produk:
        update.callback_query.edit_message_text('Produk tidak ditemukan.')
        return
    
    # Tambahkan ke keranjang
    if produk_id in keranjang[user_id]:
        if keranjang[user_id][produk_id]["jumlah"] < produk.stok:
            keranjang[user_id][produk_id]["jumlah"] += 1
        else:
            update.callback_query.edit_message_text(f'Stok {produk.nama} tidak mencukupi.')
            return
    else:
        keranjang[user_id][produk_id] = {
            "nama": produk.nama,
            "harga": produk.harga,
            "jumlah": 1
        }
    
    update.callback_query.edit_message_text(
        f'Ditambahkan: {produk.nama} - Rp {produk.harga:,.0f}\n'
        'Gunakan /keranjang untuk melihat keranjang belanja Anda.\n'
        'Gunakan /produk untuk melihat produk lainnya.'
    )

def lihat_keranjang(update: Update, context: CallbackContext) -> None:
    """Menampilkan isi keranjang belanja."""
    user_id = str(update.effective_user.id)
    
    if user_id not in keranjang or not keranjang[user_id]:
        update.message.reply_text('Keranjang belanja Anda kosong.')
        return
    
    pesan = "Keranjang Belanja Anda:\n\n"
    total = 0
    
    keyboard = []
    for produk_id, item in keranjang[user_id].items():
        subtotal = item["harga"] * item["jumlah"]
        total += subtotal
        pesan += f"{item['nama']} - {item['jumlah']} x Rp {item['harga']:,.0f} = Rp {subtotal:,.0f}\n"
        
        # Tambahkan tombol untuk menghapus produk
        keyboard.append([InlineKeyboardButton(f"Hapus {item['nama']}", callback_data=f"hapus_{produk_id}")])
    
    pesan += f"\nTotal: Rp {total:,.0f}"
    
    # Tambahkan tombol checkout dan kosongkan keranjang
    keyboard.append([InlineKeyboardButton("Checkout", callback_data="checkout")])
    keyboard.append([InlineKeyboardButton("Kosongkan Keranjang", callback_data="kosongkan")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(pesan, reply_markup=reply_markup)

def hapus_dari_keranjang(update: Update, context: CallbackContext, produk_id: str) -> None:
    """Menghapus produk dari keranjang belanja."""
    user_id = str(update.effective_user.id)
    
    if user_id in keranjang and produk_id in keranjang[user_id]:
        nama_produk = keranjang[user_id][produk_id]["nama"]
        del keranjang[user_id][produk_id]
        
        # Jika keranjang kosong setelah penghapusan
        if not keranjang[user_id]:
            update.callback_query.edit_message_text('Keranjang belanja Anda kosong.')
            return
        
        # Tampilkan kembali keranjang
        pesan = "Keranjang Belanja Anda:\n\n"
        total = 0
        
        keyboard = []
        for pid, item in keranjang[user_id].items():
            subtotal = item["harga"] * item["jumlah"]
            total += subtotal
            pesan += f"{item['nama']} - {item['jumlah']} x Rp {item['harga']:,.0f} = Rp {subtotal:,.0f}\n"
            
            # Tambahkan tombol untuk menghapus produk
            keyboard.append([InlineKeyboardButton(f"Hapus {item['nama']}", callback_data=f"hapus_{pid}")])
        
        pesan += f"\nTotal: Rp {total:,.0f}"
        
        # Tambahkan tombol checkout dan kosongkan keranjang
        keyboard.append([InlineKeyboardButton("Checkout", callback_data="checkout")])
        keyboard.append([InlineKeyboardButton("Kosongkan Keranjang", callback_data="kosongkan")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text(pesan, reply_markup=reply_markup)
    else:
        update.callback_query.edit_message_text('Produk tidak ditemukan dalam keranjang.')

def kosongkan_keranjang(update: Update, context: CallbackContext) -> None:
    """Mengosongkan keranjang belanja."""
    user_id = str(update.effective_user.id)
    
    if user_id in keranjang:
        keranjang[user_id] = {}
    
    update.callback_query.edit_message_text('Keranjang belanja Anda telah dikosongkan.')

def checkout(update: Update, context: CallbackContext) -> None:
    """Menyelesaikan transaksi."""
    user_id = str(update.effective_user.id)
    
    if user_id not in keranjang or not keranjang[user_id]:
        # Handle sesuai tipe update
        if hasattr(update, 'callback_query') and update.callback_query:
            update.callback_query.edit_message_text('Keranjang belanja Anda kosong.')
        else:
            update.message.reply_text('Keranjang belanja Anda kosong.')
        return
    
    session = get_session()
    
    # Ambil data pelanggan
    pelanggan = session.query(Pelanggan).filter_by(telegram_id=user_id).first()
    
    # Hitung total transaksi
    total = 0
    for produk_id, item in keranjang[user_id].items():
        subtotal = item["harga"] * item["jumlah"]
        total += subtotal
    
    # Buat transaksi baru
    transaksi = Transaksi(
        pelanggan_id=pelanggan.id,
        total=total,
        tanggal=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    session.add(transaksi)
    session.flush()  # Untuk mendapatkan ID transaksi
    
    # Tambahkan item transaksi dan update stok
    for produk_id, item in keranjang[user_id].items():
        produk_id_int = int(produk_id)
        transaksi_item = TransaksiItem(
            transaksi_id=transaksi.id,
            produk_id=produk_id_int,
            jumlah=item["jumlah"],
            harga_satuan=item["harga"]
        )
        session.add(transaksi_item)
        
        # Update stok produk
        produk = session.query(Produk).get(produk_id_int)
        produk.stok -= item["jumlah"]
    
    # Ambil data yang dibutuhkan untuk struk sebelum menutup sesi
    transaksi_id = transaksi.id
    transaksi_tanggal = transaksi.tanggal
    pelanggan_nama = pelanggan.nama
    
    session.commit()
    session.close()
    
    # Kirim struk transaksi menggunakan data yang sudah diambil
    struk = f"STRUK PEMBELIAN #{transaksi_id}\n"
    struk += f"Tanggal: {transaksi_tanggal}\n"
    struk += f"Pelanggan: {pelanggan_nama}\n\n"
    struk += "Detail Pembelian:\n"
    
    for produk_id, item in keranjang[user_id].items():
        subtotal = item["harga"] * item["jumlah"]
        struk += f"{item['nama']} - {item['jumlah']} x Rp {item['harga']:,.0f} = Rp {subtotal:,.0f}\n"
    
    struk += f"\nTotal: Rp {total:,.0f}"
    struk += "\n\nTerima kasih telah berbelanja!"
    
    # Kosongkan keranjang
    keranjang[user_id] = {}
    
    # ID grup untuk mengirim struk
    grup_id = -1002361168515
    
    # Kirim struk ke grup
    context.bot.send_message(chat_id=grup_id, text=struk)
    
    # Kirim struk sesuai tipe update
    if hasattr(update, 'callback_query') and update.callback_query:
        update.callback_query.edit_message_text(struk + "\n\nStruk juga telah dikirim ke grup kasir.")
    else:
        update.message.reply_text(struk + "\n\nStruk juga telah dikirim ke grup kasir.")

def main() -> None:
    """Menjalankan bot."""
    # Anda perlu mendapatkan token dari BotFather di Telegram
    updater = Updater("7968643388:AAHieL2W5nJt-JVvSRZYTTao7Q8Ub8gNUBY")
    
    dispatcher = updater.dispatcher
    
    # Menambahkan handler
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("produk", produk))
    dispatcher.add_handler(CommandHandler("keranjang", lihat_keranjang))
    dispatcher.add_handler(CommandHandler("checkout", checkout))
    dispatcher.add_handler(CallbackQueryHandler(handle_button))
    
    # Mulai bot
    updater.start_polling()
    updater.idle() 