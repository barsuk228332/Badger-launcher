import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path


class GameRunner:
    @staticmethod
    def _resolve_wine_paths(runner: str, base_prefix: Path) -> tuple[str, str, Path]:
        if runner == "System Wine" or not runner:
            return "wine", "wineserver", base_prefix

        runner_path = Path(runner)
        for sub in ["files/bin", "dist/bin", "bin"]:
            wine_candidate = runner_path / sub / "wine"
            if wine_candidate.exists():
                wineserver_candidate = runner_path / sub / "wineserver"
                actual_prefix = base_prefix / "pfx"
                return (
                    str(wine_candidate),
                    str(wineserver_candidate) if wineserver_candidate.exists() else "wineserver",
                    actual_prefix,
                )

        return "wine", "wineserver", base_prefix

    @staticmethod
    def _sanitize_prefix_path(raw_prefix: str) -> Path:
        p = Path(raw_prefix)
        if not re.search(r"\d+", str(p)):
            p = p.parent / f"{p.name}_0"
        return p

    @staticmethod
    def run_prefix_tool(runner: str, prefix_str: str, tool: str):
        base_prefix = GameRunner._sanitize_prefix_path(prefix_str)
        base_prefix.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        wine_bin, wineserver_bin, actual_prefix = GameRunner._resolve_wine_paths(
            runner, base_prefix
        )
        actual_prefix.mkdir(parents=True, exist_ok=True)

        env["WINEPREFIX"] = str(actual_prefix)
        env["STEAM_COMPAT_DATA_PATH"] = str(base_prefix)
        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(
            Path.home() / ".local/share/Steam"
        )
        env["SteamAppId"] = "0"
        env["SteamGameId"] = "0"
        env["WINE"] = wine_bin
        env["WINESERVER"] = wineserver_bin

        runner_path = Path(runner) if runner != "System Wine" else None
        proton_bin = runner_path / "proton" if runner_path else None

        if tool == "winetricks":
            if not shutil.which("winetricks"):
                raise FileNotFoundError(
                    "Утилита winetricks не найдена! Установи её через пакетный менеджер."
                )
            cmd = ["winetricks", "--gui"]
        elif tool in ("winecfg", "regedit"):
            if proton_bin and proton_bin.exists():
                cmd = [str(proton_bin), "run", tool]
            else:
                cmd = [wine_bin, tool]
        else:
            cmd = [wine_bin, tool]

        subprocess.Popen(cmd, env=env, cwd=str(base_prefix))

    @staticmethod
    def build_command_and_env(game: dict) -> tuple[list[str], dict[str, str], str]:
        env = os.environ.copy()

        raw_prefix = game.get("prefix") or str(Path.home() / "Badger" / "default_0")
        prefix_path = GameRunner._sanitize_prefix_path(raw_prefix)
        prefix_path.mkdir(parents=True, exist_ok=True)

        env["WINEPREFIX"] = str(prefix_path / "pfx")
        env["STEAM_COMPAT_DATA_PATH"] = str(prefix_path)
        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(
            Path.home() / ".local/share/Steam"
        )

        env["SteamAppId"] = "1293830"
        env["SteamGameId"] = "1293830"
        env["PROTON_NO_STEAMCLIENT"] = "1"
        env["PROTON_FORCE_LARGE_ADDRESS_AWARE"] = "1"

        existing_overrides = env.get("WINEDLLOVERRIDES", "")
        p_overrides = "lsteamclient=d;steamclient,steamclient64=n,b"
        if existing_overrides:
            env["WINEDLLOVERRIDES"] = f"{existing_overrides};{p_overrides}"
        else:
            env["WINEDLLOVERRIDES"] = p_overrides

        toggles = game.get("toggles", {})
        if toggles.get("mangohud", False):
            env["MANGOHUD"] = "1"
        if toggles.get("lsfg", False):
            env["ENABLE_LSFG"] = "1"
        if toggles.get("gamemode", False):
            pass
        if toggles.get("wayland", False):
            env["PROTON_ENABLE_WAYLAND"] = "1"

        custom_env = game.get("env_vars", {})
        for k, v in custom_env.items():
            if k.strip():
                env[k.strip()] = str(v)

        cmd = []
        if toggles.get("gamemode", False) and shutil.which("gamemoderun"):
            cmd.append("gamemoderun")

        runner = game.get("runner", "System Wine")
        exe_path = game.get("exe", "")

        if (toggles.get("use_umu", False) or runner == "System Wine") and shutil.which(
            "umu-run"
        ):
            if runner != "System Wine":
                env["PROTONPATH"] = str(Path(runner))
            env["GAMEID"] = "1293830"
            cmd.extend(["umu-run", exe_path])
        elif runner == "System Wine" or not runner:
            env["WINEPREFIX"] = str(prefix_path)
            cmd.extend(["wine", exe_path])
        else:
            runner_path = Path(runner)
            proton_bin = runner_path / "proton"
            wine_bin = runner_path / "files/bin/wine"

            if proton_bin.exists():
                cmd.extend([str(proton_bin), "waitforexitandrun", exe_path])
            elif wine_bin.exists():
                cmd.extend([str(wine_bin), exe_path])
            else:
                cmd.extend(["wine", exe_path])

        game_args = game.get("args", "").strip()
        if game_args:
            cmd.extend(shlex.split(game_args))

        work_dir = str(Path(exe_path).parent) if exe_path else str(Path.home())
        return cmd, env, work_dir