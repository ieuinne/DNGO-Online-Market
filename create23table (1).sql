-- ============================================================
-- DATABASE: DNGO - ĐI CHỢ ONLINE
-- Tổng số bảng: 23
-- ============================================================

-- ============================================================
-- 1. BẢNG KHU VỰC
-- ============================================================
CREATE TABLE khu_vuc (
    ma_khu_vuc VARCHAR(4) NOT NULL,
    phuong VARCHAR(255) NOT NULL,
    longitude FLOAT DEFAULT NULL,
    latitude FLOAT DEFAULT NULL,
    
    PRIMARY KEY (ma_khu_vuc)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 2. BẢNG CHỢ
-- ============================================================
CREATE TABLE cho_table (
    ma_cho VARCHAR(5) NOT NULL,
    ten_cho VARCHAR(255) NOT NULL,
    ma_khu_vuc VARCHAR(4) NOT NULL,
    khu_vuc VARCHAR(255) NOT NULL,
    dia_chi VARCHAR(255) NOT NULL,
    hinh_anh TEXT,
    
    PRIMARY KEY (ma_cho)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 3. BẢNG NGƯỜI DÙNG
-- ============================================================
CREATE TABLE nguoi_dung (
    ma_nguoi_dung VARCHAR(6) NOT NULL,
    ten_dang_nhap VARCHAR(255) NOT NULL,
    ten_nguoi_dung VARCHAR(255) NOT NULL,
    mat_khau VARCHAR(255) NOT NULL,
    vai_tro ENUM('nguoi_mua', 'nguoi_ban', 'shipper', 'quan_ly_cho', 'admin') NOT NULL,
    gioi_tinh CHAR(1) NOT NULL,
    so_tai_khoan VARCHAR(255) NOT NULL,
    sdt CHAR(10) NOT NULL,
    ngan_hang VARCHAR(255) NOT NULL,
    dia_chi VARCHAR(255) NOT NULL,
    tinh_trang TINYINT(1) DEFAULT 0,
    
    PRIMARY KEY (ma_nguoi_dung)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 4. BẢNG NGƯỜI MUA
-- ============================================================
CREATE TABLE nguoi_mua (
    ma_nguoi_mua VARCHAR(8) NOT NULL,
    ma_nguoi_dung VARCHAR(6) NOT NULL,
    can_nang FLOAT DEFAULT NULL,
    chieu_cao FLOAT DEFAULT NULL,
    
    PRIMARY KEY (ma_nguoi_mua),
    KEY fk_nguoimua_nguoidung (ma_nguoi_dung),
    
    CONSTRAINT fk_nguoimua_nguoidung 
        FOREIGN KEY (ma_nguoi_dung) 
        REFERENCES nguoi_dung (ma_nguoi_dung) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 5. BẢNG QUẢN LÝ CHỢ
-- ============================================================
CREATE TABLE quan_ly_cho (
    ma_quan_ly VARCHAR(8) NOT NULL,
    ma_cho VARCHAR(5) NOT NULL,
    ma_nguoi_dung VARCHAR(6) NOT NULL,
    
    PRIMARY KEY (ma_quan_ly),
    KEY fk_quanlycho_nguoidung (ma_nguoi_dung),
    KEY fk_quanlycho_cho (ma_cho),
    
    CONSTRAINT fk_quanlycho_cho 
        FOREIGN KEY (ma_cho) 
        REFERENCES cho_table (ma_cho) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_quanlycho_nguoidung 
        FOREIGN KEY (ma_nguoi_dung) 
        REFERENCES nguoi_dung (ma_nguoi_dung) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 6. BẢNG GIAN HÀNG
-- ============================================================
CREATE TABLE gian_hang (
    ma_gian_hang VARCHAR(8) NOT NULL,
    ten_gian_hang VARCHAR(255) NOT NULL,
    ma_cho VARCHAR(5) NOT NULL,
    ma_nguoi_dung VARCHAR(6) NOT NULL,
    ma_quan_ly VARCHAR(8) DEFAULT NULL,
    vi_tri VARCHAR(255) NOT NULL,
    hinh_anh TEXT,
    danh_gia_tb FLOAT,
    ngay_dang_ky DATE NOT NULL,
    
    PRIMARY KEY (ma_gian_hang),
    KEY fk_gianhang_cho (ma_cho),
    KEY fk_gianhang_nguoidung (ma_nguoi_dung),
    KEY fk_gianhang_quanlycho (ma_quan_ly),
    
    CONSTRAINT fk_gianhang_cho 
        FOREIGN KEY (ma_cho) 
        REFERENCES cho_table (ma_cho) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_gianhang_nguoidung 
        FOREIGN KEY (ma_nguoi_dung) 
        REFERENCES nguoi_dung (ma_nguoi_dung) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_gianhang_quanlycho 
        FOREIGN KEY (ma_quan_ly) 
        REFERENCES quan_ly_cho (ma_quan_ly) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 7. BẢNG SHIPPER
-- ============================================================
CREATE TABLE shipper (
    ma_shipper VARCHAR(8) NOT NULL,
    ma_nguoi_dung VARCHAR(6) NOT NULL,
    phuong_tien VARCHAR(255) NOT NULL,
    bien_so_xe VARCHAR(255) NOT NULL,
    
    PRIMARY KEY (ma_shipper),
    KEY fk_shipper_nguoidung (ma_nguoi_dung),
    
    CONSTRAINT fk_shipper_nguoidung 
        FOREIGN KEY (ma_nguoi_dung) 
        REFERENCES nguoi_dung (ma_nguoi_dung) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 8. BẢNG NHÓM NGUYÊN LIỆU
-- ============================================================
CREATE TABLE nhom_nguyen_lieu (
    ma_nhom_nguyen_lieu VARCHAR(3) NOT NULL,
    ten_nhom_nguyen_lieu VARCHAR(255) NOT NULL,
    loai_nhom_nguyen_lieu VARCHAR(255) NOT NULL,
    
    PRIMARY KEY (ma_nhom_nguyen_lieu)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 9. BẢNG NGUYÊN LIỆU
-- ============================================================
CREATE TABLE nguyen_lieu (
    ma_nguyen_lieu VARCHAR(10) NOT NULL,
    ten_nguyen_lieu VARCHAR(255) NOT NULL,
    ma_nhom_nguyen_lieu VARCHAR(3) NOT NULL,
    don_vi VARCHAR(255) DEFAULT NULL,
    
    PRIMARY KEY (ma_nguyen_lieu),
    KEY fk_nguyenlieu_nhomnguyenlieu (ma_nhom_nguyen_lieu),
    
    CONSTRAINT fk_nguyenlieu_nhomnguyenlieu 
        FOREIGN KEY (ma_nhom_nguyen_lieu) 
        REFERENCES nhom_nguyen_lieu (ma_nhom_nguyen_lieu) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 10. BẢNG SẢN PHẨM BÁN
-- ============================================================
CREATE TABLE san_pham_ban (
    ma_nguyen_lieu VARCHAR(10) NOT NULL,
    ma_gian_hang VARCHAR(8) NOT NULL,
    hinh_anh TEXT NOT NULL,
    so_luong_ban FLOAT NOT NULL,
    gia_goc INT NOT NULL,
    phan_tram_giam_gia FLOAT,
    ngay_cap_nhat DATETIME NOT NULL,
    thoi_gian_bat_dau_giam DATETIME DEFAULT NULL,
    thoi_gian_ket_thuc_giam DATETIME DEFAULT NULL,
    don_vi_ban VARCHAR(255) NOT NULL,
    gia_cuoi DECIMAL(10,2) GENERATED ALWAYS AS (gia_goc * (1 - phan_tram_giam_gia / 100)) STORED,
    
    PRIMARY KEY (ma_nguyen_lieu, ma_gian_hang),
    KEY fk_sanphamban_gianhang (ma_gian_hang),
    
    CONSTRAINT fk_sanphamban_gianhang 
        FOREIGN KEY (ma_gian_hang) 
        REFERENCES gian_hang (ma_gian_hang) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_sanphamban_nguyenlieu 
        FOREIGN KEY (ma_nguyen_lieu) 
        REFERENCES nguyen_lieu (ma_nguyen_lieu) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 11. BẢNG DANH MỤC MÓN ĂN
-- ============================================================
CREATE TABLE danh_muc_mon_an (
    ma_danh_muc_mon_an VARCHAR(4) NOT NULL,
    ten_danh_muc_mon_an VARCHAR(255) NOT NULL,
    loai_danh_muc VARCHAR(255) NOT NULL,
    
    PRIMARY KEY (ma_danh_muc_mon_an)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 12. BẢNG MÓN ĂN
-- ============================================================
CREATE TABLE mon_an (
    ma_mon_an VARCHAR(5) NOT NULL,
    ten_mon_an VARCHAR(255) NOT NULL,
    hinh_anh TEXT,
    khoang_thoi_gian INT DEFAULT NULL,
    do_kho VARCHAR(255) DEFAULT NULL,
    khau_phan_tieu_chuan INT NOT NULL,
    cach_thuc_hien TEXT NOT NULL,
    so_che TEXT,
    cach_dung TEXT,
    calories FLOAT DEFAULT NULL,
    
    PRIMARY KEY (ma_mon_an)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 13. BẢNG PHÂN LOẠI MÓN ĂN
-- ============================================================
CREATE TABLE phan_loai_mon_an (
    ma_danh_muc_mon_an VARCHAR(4) NOT NULL,
    ma_mon_an VARCHAR(5) NOT NULL,
    
    PRIMARY KEY (ma_danh_muc_mon_an, ma_mon_an),
    KEY fk_phanloai_monan (ma_mon_an),
    
    CONSTRAINT fk_phanloai_danhmuc 
        FOREIGN KEY (ma_danh_muc_mon_an) 
        REFERENCES danh_muc_mon_an (ma_danh_muc_mon_an) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_phanloai_monan 
        FOREIGN KEY (ma_mon_an) 
        REFERENCES mon_an (ma_mon_an) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 14. BẢNG CÔNG THỨC MÓN ĂN
-- ============================================================
CREATE TABLE cong_thuc_mon_an (
    ID INT NOT NULL AUTO_INCREMENT,
    ma_mon_an VARCHAR(5) NOT NULL,
    ma_nguyen_lieu VARCHAR(10) NOT NULL,
    ten_nguyen_lieu VARCHAR(255) DEFAULT NULL,
    dinh_luong VARCHAR(255) DEFAULT NULL,
    
    PRIMARY KEY (ID),
    KEY fk_congthuc_monan (ma_mon_an),
    KEY fk_congthuc_nguyenlieu (ma_nguyen_lieu),
    
    CONSTRAINT fk_congthuc_monan 
        FOREIGN KEY (ma_mon_an) 
        REFERENCES mon_an (ma_mon_an) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_congthuc_nguyenlieu 
        FOREIGN KEY (ma_nguyen_lieu) 
        REFERENCES nguyen_lieu (ma_nguyen_lieu) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=88206 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 15. BẢNG GIỎ HÀNG
-- ============================================================
CREATE TABLE gio_hang (
    ma_gio_hang VARCHAR(10) NOT NULL,
    ma_nguoi_mua VARCHAR(8) NOT NULL,
    ngay_tao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ngay_cap_nhat DATETIME NOT NULL,
    
    PRIMARY KEY (ma_gio_hang),
    KEY fk_giohang_nguoimua (ma_nguoi_mua)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 16. BẢNG CHI TIẾT GIỎ HÀNG
-- ============================================================
CREATE TABLE chi_tiet_gio_hang (
    ma_gio_hang VARCHAR(10) NOT NULL,
    ma_nguyen_lieu VARCHAR(10) NOT NULL,
    ma_gian_hang VARCHAR(8) NOT NULL,
    so_luong FLOAT NOT NULL,
    ngay_them DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (ma_gio_hang, ma_nguyen_lieu, ma_gian_hang),
    KEY fk_chitietgiohang_nguyenlieu (ma_nguyen_lieu),
    KEY fk_chitietgiohang_gianhang (ma_gian_hang),
    
    CONSTRAINT fk_chitietgiohang_giohang 
        FOREIGN KEY (ma_gio_hang) 
        REFERENCES gio_hang (ma_gio_hang) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 17. BẢNG THANH TOÁN
-- ============================================================
CREATE TABLE thanh_toan (
    ma_thanh_toan VARCHAR(10) NOT NULL,
    hinh_thuc_thanh_toan ENUM('chuyen_khoan', 'tien_mat') NOT NULL DEFAULT 'tien_mat',
    tai_khoan_thanh_toan VARCHAR(255) NOT NULL,
    thoi_gian_thanh_toan DATETIME NOT NULL,
    tinh_trang_thanh_toan ENUM('chua_thanh_toan', 'da_thanh_toan') NOT NULL DEFAULT 'chua_thanh_toan',
    
    PRIMARY KEY (ma_thanh_toan)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 18. BẢNG ĐỌN HÀNG
-- ============================================================
CREATE TABLE don_hang (
    ma_don_hang VARCHAR(10) NOT NULL,
    ma_thanh_toan VARCHAR(10) DEFAULT NULL,
    ma_nguoi_mua VARCHAR(8) NOT NULL,
    tong_tien INT DEFAULT NULL,
    dia_chi_giao_hang VARCHAR(255) NOT NULL,
    tinh_trang_don_hang ENUM('chua_xac_nhan', 'da_xac_nhan', 'dang_giao', 'da_giao', 'da_huy', 'hoan_thanh') NOT NULL DEFAULT 'chua_xac_nhan',
    thoi_gian_giao_hang DATETIME NOT NULL,
    
    PRIMARY KEY (ma_don_hang),
    KEY fk_donhang_thanhtoan (ma_thanh_toan),
    KEY fk_donhang_nguoimua (ma_nguoi_mua),
    
    CONSTRAINT fk_donhang_nguoimua 
        FOREIGN KEY (ma_nguoi_mua) 
        REFERENCES nguoi_mua (ma_nguoi_mua) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_donhang_thanhtoan 
        FOREIGN KEY (ma_thanh_toan) 
        REFERENCES thanh_toan (ma_thanh_toan) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 19. BẢNG CHI TIẾT ĐƠN HÀNG
-- ============================================================
CREATE TABLE chi_tiet_don_hang (
    ma_don_hang VARCHAR(10) NOT NULL,
    ma_nguyen_lieu VARCHAR(10) NOT NULL,
    ma_gian_hang VARCHAR(8) NOT NULL,
    so_luong FLOAT NOT NULL,
    gia_cuoi INT DEFAULT NULL,
    ma_mon_an VARCHAR(255) DEFAULT NULL,
    thanh_tien INT GENERATED ALWAYS AS (so_luong * gia_cuoi) STORED,
    
    PRIMARY KEY (ma_don_hang, ma_nguyen_lieu, ma_gian_hang)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 20. BẢNG KHUNG GIỜ
-- ============================================================
CREATE TABLE khung_gio (
    ma_khung_gio VARCHAR(4) NOT NULL,
    gio_bat_dau TIME NOT NULL,
    gio_ket_thuc TIME NOT NULL,
    
    PRIMARY KEY (ma_khung_gio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 21. BẢNG GOM ĐƠN
-- ============================================================
CREATE TABLE gom_don (
    ma_gom_don VARCHAR(10) NOT NULL,
    ma_shipper VARCHAR(8) NOT NULL,
    ma_don_hang VARCHAR(10) NOT NULL,
    ma_khung_gio VARCHAR(4) NOT NULL,
    ma_khu_vuc VARCHAR(4) NOT NULL,
    
    PRIMARY KEY (ma_gom_don),
    KEY fk_gomdon_shipper (ma_shipper),
    KEY fk_gomdon_donhang (ma_don_hang),
    KEY fk_gomdon_khunggio (ma_khung_gio),
    KEY fk_gomdon_khu_vuc (ma_khu_vuc),
    
    CONSTRAINT fk_gomdon_donhang 
        FOREIGN KEY (ma_don_hang) 
        REFERENCES don_hang (ma_don_hang) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_gomdon_khu_vuc 
        FOREIGN KEY (ma_khu_vuc) 
        REFERENCES khu_vuc (ma_khu_vuc) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_gomdon_khunggio 
        FOREIGN KEY (ma_khung_gio) 
        REFERENCES khung_gio (ma_khung_gio) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_gomdon_shipper 
        FOREIGN KEY (ma_shipper) 
        REFERENCES shipper (ma_shipper) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 22. BẢNG ĐÁNH GIÁ
-- ============================================================
CREATE TABLE danh_gia (
    ma_danh_gia VARCHAR(10) NOT NULL,
    ma_nguoi_mua VARCHAR(8) NOT NULL,
    ma_gian_hang VARCHAR(8) NOT NULL,
    ngay_danh_gia DATETIME NOT NULL,
    rating INT DEFAULT NULL,
    binh_luan TEXT,
    ma_don_hang VARCHAR(10) NOT NULL,
    ma_nguyen_lieu VARCHAR(10) NOT NULL,
    
    PRIMARY KEY (ma_danh_gia),
    UNIQUE KEY danh_gia_unique (ma_nguoi_mua, ma_don_hang, ma_nguyen_lieu, ma_gian_hang),
    KEY fk_danhgia_gianhang (ma_gian_hang),
    KEY fk_danhgia_donhang (ma_don_hang),
    KEY fk_danhgia_nguoimua (ma_nguoi_mua),
    
    CONSTRAINT fk_danhgia_donhang 
        FOREIGN KEY (ma_don_hang) 
        REFERENCES don_hang (ma_don_hang) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_danhgia_gianhang 
        FOREIGN KEY (ma_gian_hang) 
        REFERENCES gian_hang (ma_gian_hang) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_danhgia_nguoimua 
        FOREIGN KEY (ma_nguoi_mua) 
        REFERENCES nguoi_mua (ma_nguoi_mua) 
        ON DELETE RESTRICT 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- ============================================================
-- 23. BẢNG RAWDATA TEST (Dữ liệu thô để xử lý)
-- ============================================================
CREATE TABLE rawdata_test (
    Calories TEXT,
    `Cách dùng` TEXT,
    `Cách thực hiện` TEXT,
    `Danh mục món ăn` TEXT,
    `Hình ảnh` VARCHAR(2000) DEFAULT NULL,
    `Khẩu phần` VARCHAR(10) DEFAULT NULL,
    `Link món ăn` VARCHAR(2000) DEFAULT NULL,
    `Nguyên liệu` TEXT,
    `Sơ chế` TEXT,
    `Thời gian thực hiện` VARCHAR(10) DEFAULT NULL,
    `Tên món ăn` VARCHAR(255) DEFAULT NULL,
    `Độ khó` VARCHAR(20) DEFAULT NULL,
    tinh_trang_xu_ly TINYINT(1) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
