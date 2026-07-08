from flash_earn_reminder.instance_guard import build_instance_key


def test_build_instance_key_is_stable_for_same_path() -> None:
    path = r"D:\mycode\webload"

    left = build_instance_key(path)
    right = build_instance_key(path)

    assert left == right
    assert left.startswith("okx_flash_earn_reminder_")
