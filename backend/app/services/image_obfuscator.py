"""
Image Obfuscation Service
图片加扰/解扰服务，支持密码保护
"""
import hashlib
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


def _derive_key(password: str, salt: bytes = b'sd-sorter-salt-2026') -> bytes:
    """从密码派生 AES 密钥"""
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key[:32]  # AES-256 需要 32 字节


def obfuscate_image(
    input_path: Path,
    output_path: Path,
    password: str,
    method: str = 'xor'
) -> bool:
    """
    加扰图片

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        password: 密码
        method: 加扰方法 ('xor', 'aes')

    Returns:
        是否成功
    """
    try:
        img = Image.open(input_path)
        img_array = np.array(img)

        if method == 'xor':
            # XOR 加密（快速但不够安全）
            key = _derive_key(password)
            key_array = np.frombuffer(key, dtype=np.uint8)

            # 扩展密钥到图像大小
            flat_img = img_array.flatten()
            key_repeated = np.tile(key_array, (len(flat_img) // len(key_array)) + 1)[:len(flat_img)]

            # XOR 操作
            obfuscated = np.bitwise_xor(flat_img, key_repeated)
            obfuscated_img = obfuscated.reshape(img_array.shape)

        elif method == 'aes':
            # AES 加密（更安全但较慢）
            key = _derive_key(password)
            iv = hashlib.sha256(password.encode()).digest()[:16]

            cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            flat_img = img_array.flatten().tobytes()
            encrypted = encryptor.update(flat_img) + encryptor.finalize()

            obfuscated_img = np.frombuffer(encrypted, dtype=np.uint8).reshape(img_array.shape)

        else:
            logger.error(f"Unknown obfuscation method: {method}")
            return False

        # 保存加扰图片
        obfuscated_pil = Image.fromarray(obfuscated_img.astype(np.uint8), mode=img.mode)
        obfuscated_pil.save(output_path, format=img.format or 'PNG')

        logger.info(f"Obfuscated {input_path} -> {output_path} using {method}")
        return True

    except Exception as e:
        logger.error(f"Failed to obfuscate image: {e}")
        return False


def deobfuscate_image(
    input_path: Path,
    output_path: Path,
    password: str,
    method: str = 'xor'
) -> bool:
    """
    解扰图片

    Args:
        input_path: 加扰的图片路径
        output_path: 输出原图路径
        password: 密码
        method: 解扰方法 ('xor', 'aes')

    Returns:
        是否成功
    """
    try:
        img = Image.open(input_path)
        img_array = np.array(img)

        if method == 'xor':
            # XOR 解密（对称操作）
            key = _derive_key(password)
            key_array = np.frombuffer(key, dtype=np.uint8)

            flat_img = img_array.flatten()
            key_repeated = np.tile(key_array, (len(flat_img) // len(key_array)) + 1)[:len(flat_img)]

            deobfuscated = np.bitwise_xor(flat_img, key_repeated)
            deobfuscated_img = deobfuscated.reshape(img_array.shape)

        elif method == 'aes':
            # AES 解密
            key = _derive_key(password)
            iv = hashlib.sha256(password.encode()).digest()[:16]

            cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
            decryptor = cipher.decryptor()

            flat_img = img_array.flatten().tobytes()
            decrypted = decryptor.update(flat_img) + decryptor.finalize()

            deobfuscated_img = np.frombuffer(decrypted, dtype=np.uint8).reshape(img_array.shape)

        else:
            logger.error(f"Unknown deobfuscation method: {method}")
            return False

        # 保存解扰图片
        deobfuscated_pil = Image.fromarray(deobfuscated_img.astype(np.uint8), mode=img.mode)
        deobfuscated_pil.save(output_path, format=img.format or 'PNG')

        logger.info(f"Deobfuscated {input_path} -> {output_path} using {method}")
        return True

    except Exception as e:
        logger.error(f"Failed to deobfuscate image: {e}")
        return False


def obfuscate_simple(
    input_path: Path,
    output_path: Path,
    seed: int = 42
) -> bool:
    """
    简单加扰（无密码，基于随机种子）
    适合快速混淆，不适合保密

    Args:
        input_path: 输入图片
        output_path: 输出图片
        seed: 随机种子

    Returns:
        是否成功
    """
    try:
        img = Image.open(input_path)
        img_array = np.array(img)

        # 使用随机种子生成置换序列
        rng = np.random.RandomState(seed)
        flat_img = img_array.flatten()

        # 生成置换索引
        indices = np.arange(len(flat_img))
        rng.shuffle(indices)

        # 打乱像素
        shuffled = flat_img[indices]
        obfuscated_img = shuffled.reshape(img_array.shape)

        # 保存
        obfuscated_pil = Image.fromarray(obfuscated_img.astype(np.uint8), mode=img.mode)
        obfuscated_pil.save(output_path, format=img.format or 'PNG')

        logger.info(f"Simple obfuscation: {input_path} -> {output_path} (seed={seed})")
        return True

    except Exception as e:
        logger.error(f"Failed simple obfuscation: {e}")
        return False


def deobfuscate_simple(
    input_path: Path,
    output_path: Path,
    seed: int = 42
) -> bool:
    """
    简单解扰

    Args:
        input_path: 加扰的图片
        output_path: 输出原图
        seed: 随机种子（必须与加扰时相同）

    Returns:
        是否成功
    """
    try:
        img = Image.open(input_path)
        img_array = np.array(img)

        # 使用相同种子生成相同的置换序列
        rng = np.random.RandomState(seed)
        flat_img = img_array.flatten()

        # 生成置换索引
        indices = np.arange(len(flat_img))
        rng.shuffle(indices)

        # 创建逆置换
        inverse_indices = np.argsort(indices)

        # 恢复像素
        restored = flat_img[inverse_indices]
        deobfuscated_img = restored.reshape(img_array.shape)

        # 保存
        deobfuscated_pil = Image.fromarray(deobfuscated_img.astype(np.uint8), mode=img.mode)
        deobfuscated_pil.save(output_path, format=img.format or 'PNG')

        logger.info(f"Simple deobfuscation: {input_path} -> {output_path} (seed={seed})")
        return True

    except Exception as e:
        logger.error(f"Failed simple deobfuscation: {e}")
        return False


def verify_password(password: str, obfuscated_path: Path, method: str = 'xor') -> bool:
    """
    验证密码是否正确（通过尝试解扰一小块区域）

    Args:
        password: 待验证的密码
        obfuscated_path: 加扰的图片
        method: 加扰方法

    Returns:
        密码是否正确（启发式判断）
    """
    try:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = Path(tmp.name)

        # 尝试解扰
        success = deobfuscate_image(obfuscated_path, tmp_path, password, method)

        if not success:
            return False

        # 检查解扰结果是否像正常图片
        try:
            img = Image.open(tmp_path)
            img_array = np.array(img)

            # 启发式判断：正常图片的像素值应该有一定的连续性和规律
            # 计算梯度，正常图片的梯度应该较小
            if len(img_array.shape) >= 2:
                grad_x = np.abs(np.diff(img_array, axis=0))
                grad_y = np.abs(np.diff(img_array, axis=1))

                avg_grad = (np.mean(grad_x) + np.mean(grad_y)) / 2

                # 如果平均梯度过大，说明可能是噪声（密码错误）
                if avg_grad > 100:  # 阈值可调
                    return False

            return True

        finally:
            tmp_path.unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Failed to verify password: {e}")
        return False
