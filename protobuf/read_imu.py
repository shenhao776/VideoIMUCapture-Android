import os
import datetime
# 导入刚刚编译出来的编译文件
from recording_pb2 import VideoCaptureData

def extract_imu_data_with_global_time(pb3_path, output_csv_path=None):
    """
    读取 video_meta.pb3 文件，提取 IMU 数据，并将其转换为全局真实时间 (YYYY-MM-DD HH:MM:SS.fff)
    """
    if not os.path.exists(pb3_path):
        print(f"错误: 找不到文件 {pb3_path}")
        return

    print(f"正在读取文件: {pb3_path} ...")
    
    # 1. 以二进制流读取 pb3 文件
    with open(pb3_path, 'rb') as f:
        video_capture_data = VideoCaptureData.FromString(f.read())
    
    # 2. 打印基础元信息
    print("\n=== IMU 设备信息 ===")
    print(f"陀螺仪配置: {video_capture_data.imu_meta.gyro_info}")
    print(f"加速度计配置: {video_capture_data.imu_meta.accel_info}")
    print(f"采样频率: {video_capture_data.imu_meta.sample_frequency} Hz")
    
    # --- 3. 核心时间转换逻辑：获取全局绝对时间的锚点 ---
    # protobuf 中记录的是录制触发那一刻的真实世界绝对时间
    start_time_sec = video_capture_data.time.seconds
    start_time_nanos = video_capture_data.time.nanos
    global_start_time_ns = int(start_time_sec * 1e9 + start_time_nanos)
    
    # 打印给用户确认
    real_world_start = datetime.datetime.fromtimestamp(start_time_sec + start_time_nanos / 1e9)
    print(f"\n录制开始的绝对时间锚点: {real_world_start.strftime('%Y-%m-%d %H:%M:%S.%f')}")
    
    imu_list = video_capture_data.imu
    total_samples = len(imu_list)
    if total_samples == 0:
        print("未在文件中找到 IMU 数据！")
        return

    print(f"开始解析共 {total_samples} 条 IMU 数据条目...\n")

    # 提取第一帧的开机时间（boot_time）作为相对时间计算的基准点
    first_imu_boot_ns = imu_list[0].time_ns

    # 4. 准备写入 CSV
    header = "global_time,timestamp_ns,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z"
    extracted_lines = []

    for imu_sample in imu_list:
        # 获取原始的硬件级开机纳秒时间戳
        timestamp_ns = imu_sample.time_ns
        
        # 计算当前帧对应的全局 UNIX 纳秒时间：
        # 全局绝对时间 = 绝对时间锚点 + (当前帧相对时间 - 首帧相对时间)
        elapsed_ns = timestamp_ns - first_imu_boot_ns
        current_global_ns = global_start_time_ns + elapsed_ns
        
        # 将纳秒转换回秒，为了让 datetime 模块能将其格式化为人类可读格式
        current_global_sec = current_global_ns / 1e9
        current_dt = datetime.datetime.fromtimestamp(current_global_sec)
        
        # 格式化时间字符串：包含年月日时分秒，以及微秒（%f），方便精确对齐 log
        global_time_str = current_dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # 提取加速度计与陀螺仪的原始数据
        accel = imu_sample.accel
        gyro = imu_sample.gyro
        
        # 组装成逗号分隔的字符串
        line = f"{global_time_str},{timestamp_ns},{accel[0]},{accel[1]},{accel[2]},{gyro[0]},{gyro[1]},{gyro[2]}"
        extracted_lines.append(line)

    # 5. 导出保存为 CSV
    if output_csv_path:
        with open(output_csv_path, 'w') as f_out:
            f_out.write(header + '\n')
            f_out.write('\n'.join(extracted_lines) + '\n')
        print(f"解析完成！带有全局绝对时间的 IMU 数据已导出至: {output_csv_path}")

if __name__ == "__main__":
    # 请确认此处的文件名与你在测试目录中的一致
    PB3_FILE = "video_meta.pb3" 
    OUTPUT_CSV = "imu_output.csv"
    
    extract_imu_data_with_global_time(PB3_FILE, OUTPUT_CSV)
