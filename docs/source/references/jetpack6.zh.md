# G1 JetPack 6 刷机指南

## 1. 下载镜像

1. **下载所需文件** — 从 [Jetpack 6.2](https://drive.google.com/drive/folders/1ho17ectOxi7FbaRFdpAbP4tet8BJWjbm) 获取 `.tar` 文件和镜像文件。

## 2. 卸载 Orin NX 的 NVMe

### 拆卸 NVMe SSD 的步骤

1. **拆下背部手柄螺丝**

   使用 5 mm T 型内六角扳手拧下机器人背部手柄附近的两个螺丝。

2. **取下泡沫和塑料后盖**

   - 使用 Fanttik 工具包中的 2 mm 内六角工具拧下固定泡沫和塑料背板的四颗螺丝。
   - 取下背板，露出内部组件。

```{image} ../_static/screws.png
:width: 600px
:align: center
```

3. **拆下 Orin NX 模块上的 NVMe 螺丝**

   使用 Fanttik 工具包中的十字螺丝刀拧下固定 Orin NX NVMe SSD 的单颗螺丝。

```{image} ../_static/ssd.png
:width: 600px
:align: center
```

4. **取出 SSD 卡**

   小心地从插槽中滑出并取下 NVMe SSD。

## 3. 刷写 NVMe SSD

**将 Orin NX 的 NVMe SSD 装入 NVMe SSD 外置盒适配器中。**
（从笔记本电脑烧录镜像时需要适配器）

1. 确认机器人的 SSD 已卸载。运行以下命令确保外置 SSD（即将烧录镜像的目标盘）未挂载：

```bash
sudo umount /dev/sda*
```

2. 如果 SSD 已挂载，此命令会安全卸载它，使其准备好接收镜像。

3. 导航到存放镜像的文件夹（`cd robot_NXUpgrade/`），然后运行以下命令：

```bash
bzip2 -dc g1-nx-j6.2.img.bz2 | sudo dd of=/dev/sda bs=4M status=progress conv=fsync
```

4. 完成后，使用以下命令安全弹出卡片：

```bash
sudo sync
sudo udisksctl power-off -b /dev/sda
```

5. **将 SSD 卡放到一边，继续进行刷机流程的第二部分！**

## 4. 将机器人置于刷机模式

1. **给 G1 上电** 并等待三个电源指示灯全部常亮。

2. **使用 USB-C 线将机器人连接到您的笔记本电脑/台式机**。

3. **同时按住两个白色按钮** 两秒钟。

4. 在按住的同时，**松开上方白色按钮** 并继续按住 **下方按钮** 2 秒钟，直到 **三个绿灯变为两个绿灯**。

```{image} ../_static/flashing.png
:width: 600px
:align: center
```

5. 当只有两个灯亮时，机器人 **已进入刷机模式**。在计算机上打开新终端并输入 `lsusb`。您应该看到包含 `NVIDIA Corp. APX` 的文本。

6. 现在可以运行以下命令：

```bash
sudo tar -xjvf Jetpack_6.2_nx.tar.bz2
cd Jetpack_6.2_nx/Linux_for_Tegra
sudo ./flash_nx_module.sh
```

耐心等待约 8 分钟，直到显示成功。

## 5. 重新组装机器人

1. 刷机完成后，**关闭机器人电源**。

2. **将 Orin NX 的 NVMe SSD 重新装回** G1 机器人上的插槽，并用螺丝固定。

3. **重新安装泡沫和塑料背板**，使用拆卸时相同的工具。

4. **拧紧所有螺丝**，确保后盖和手柄牢固就位。

5. 在 Jetson Orin 上使用以下命令开启 `maxn` 模式：


```
sudo nvpmodel -m 0
```

并使用


```
sudo jetson_clocks
sudo jetson_clocks --show  
```

检查是否已进入 Maxn 模式。
