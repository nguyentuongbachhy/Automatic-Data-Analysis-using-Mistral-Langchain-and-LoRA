import os
import glob
import zipfile
import shutil # Sử dụng shutil để nén thư mục dễ dàng hơn (Cách 1)

# --- Tùy chọn cách làm ---
USE_SHUTIL = True # Đặt thành False nếu muốn dùng cách os.walk thủ công (Cách 2)

# ----- Cấu hình -----
source_base_dir = "models/lora-intent-detection-v2/" # Thư mục chứa các thư mục con cần nén
output_dir = "output/" # Thư mục lưu các file .zip

# ----- Thực thi -----

# Tạo thư mục output nếu nó không tồn tại
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Tạo thư mục: {output_dir}")

# Lặp qua tất cả các mục trong thư mục nguồn
print(f"Bắt đầu quét trong: {source_base_dir}")
items_to_process = glob.glob(os.path.join(source_base_dir, "*"))
print(f"Tìm thấy {len(items_to_process)} mục.")

if not items_to_process:
    print(f"Cảnh báo: Không tìm thấy thư mục con nào trong '{source_base_dir}' để nén.")

for item_path in items_to_process:
    # Chỉ xử lý nếu nó là một thư mục
    if os.path.isdir(item_path):
        folder_name = os.path.basename(item_path)
        # Đường dẫn đến tệp zip sẽ được tạo trong thư mục output
        zip_file_path = os.path.join(output_dir, f"{folder_name}.zip")

        print(f"\nĐang xử lý thư mục: {item_path}")
        print(f"Sẽ tạo tệp zip tại: {zip_file_path}")

        if USE_SHUTIL:
            # --- Cách 1: Dùng shutil.make_archive (đơn giản và khuyến nghị) ---
            try:
                # shutil.make_archive tạo tệp zip chứa nội dung của item_path
                # 'zip' là định dạng
                # output_dir là nơi lưu tệp zip (nó sẽ tự thêm .zip)
                # item_path là thư mục cần nén
                # basename là tên file zip không có đuôi .zip
                shutil.make_archive(base_name=os.path.join(output_dir, folder_name),
                                    format='zip',
                                    root_dir=item_path) # Nén nội dung BÊN TRONG item_path
                print(f"Đã tạo thành công (dùng shutil): {zip_file_path}")
            except Exception as e:
                print(f"Lỗi khi tạo zip cho {item_path} bằng shutil: {e}")

        else:
            # --- Cách 2: Dùng zipfile và os.walk (thủ công) ---
            try:
                with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Lấy độ dài của đường dẫn thư mục cha để tạo đường dẫn tương đối
                    len_dir_path = len(item_path) + len(os.path.sep)
                    # Duyệt qua tất cả các tệp và thư mục con
                    for root, dirs, files in os.walk(item_path):
                        # Tính toán đường dẫn tương đối bên trong tệp zip
                        relative_root = root[len_dir_path:] # Bỏ phần đường dẫn gốc

                        # Thêm các thư mục con (để giữ cấu trúc thư mục rỗng nếu có)
                        # for d in dirs:
                        #    dir_arcname = os.path.join(relative_root, d)
                        #    # Thường không cần thêm thư mục rõ ràng, zipfile tự tạo khi thêm file
                        #    # print(f"  Adding dir: {dir_arcname}")
                        #    # zipf.write(os.path.join(root, d), arcname=dir_arcname) # Cẩn thận, không cần thiết lắm

                        # Thêm các tệp tin
                        for file in files:
                            file_path = os.path.join(root, file)
                            # arcname là đường dẫn của tệp bên trong tệp zip
                            arcname = os.path.join(relative_root, file)
                            # print(f"  Adding file: {file_path} as {arcname}")
                            zipf.write(file_path, arcname=arcname)

                print(f"Đã tạo thành công (dùng zipfile): {zip_file_path}")
            except Exception as e:
                print(f"Lỗi khi tạo zip cho {item_path} bằng zipfile: {e}")
    else:
        # Bỏ qua nếu không phải là thư mục
        print(f"\nBỏ qua mục: {item_path} (không phải thư mục)")

print("\nHoàn tất quá trình nén.")