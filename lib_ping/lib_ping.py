# STDLIB
import re
import subprocess

# OWN
import lib_platform
import lib_shell


class ResponseObject(object):
    def __init__(self) -> None:
        # init values for not reached condition
        # old typing syntax for python 3.5
        self.target = ''                        # type: str    # the target (input) - can be IP or Hostname
        self.reached = False                    # type: bool
        self.ip = '0.0.0.0'                     # type: str    # the IP Adress (output) of the Target
        self.number_of_pings = 0                # type: int
        self.time_min_ms = -1                   # type: float
        self.time_avg_ms = -1                   # type: float
        self.time_max_ms = -1                   # type: float
        self.n_packets_lost = 0                 # type: int
        self.packets_lost_percentage = 100      # type: int
        self.str_result = ''                    # type: str


def ping(target: str, times: int = 4) -> ResponseObject:
    """

    >>> ping('www.google.com')  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    <...ResponseObject object at ...>

    >>> response = ping('1.1.1.1', 1)
    >>> assert response.reached
    >>> assert response.packets_lost_percentage == 0

    >>> response = ping('10.0.0.1', 1)
    >>> assert not response.reached

    >>> response = ping('www.google.com', 1)
    >>> assert response.reached


    """

    response = ResponseObject()
    response.target = target
    response.number_of_pings = times

    try:
        if lib_platform.is_platform_linux:
            ping_result = ping_linux(target=target, times=times)
        elif lib_platform.is_platform_darwin:
            ping_result = ping_darwin(target=target, times=times)
        else:
            ping_result = ping_windows(target=target)

        text = ping_result.stdout.replace('\r\n', '\n').replace('\r', '\n')

        # match IP address in format: [192.168.1.1] (192.168.1.1)
        ip = re.findall(r'(?<=[(\[])\d+\.\d+\.\d+\.\d+(?=[)\]])', text)
        if not ip:
            ip = re.findall(r'\d+\.\d+\.\d+\.\d+', text)
        response.ip = ip[0] if ip else '0.0.0.0'

        # avg ping time
        if lib_platform.is_platform_posix:
            time = re.findall(r'(?=\d+\.\d+/)(\d+\.\d+)+', text)
            if time:                                                                                                     # pragma: no cover
                response.time_min_ms = float(time[0])
                response.time_avg_ms = float(time[1])
                response.time_max_ms = float(time[2])
        else:
            time = re.findall(r'(\d+(?=ms))+', text)
            if time:                                                                                                     # pragma: no cover
                response.time_avg_ms = float(time[len(time) - 1])
                response.time_max_ms = float(time[len(time) - 2])
                response.time_min_ms = float(time[len(time) - 3])

        if not time:                                                                                                     # pragma: no cover
            response.time_min_ms = response.time_avg_ms = response.time_max_ms = -1                                      # pragma: no cover

        # packet loss rate
        lost = re.findall(r'\d+.\d+(?=%)', text)
        if not lost:
            lost = re.findall(r'\d+(?=%)', text)

        response.n_packets_lost = len(lost)
        response.packets_lost_percentage = int(round(float(lost[len(lost) - 1]))) if lost else 100
        if response.packets_lost_percentage < 100:                                                                       # pragma: no cover
            response.reached = True
        _create_str_result(response=response)
    except subprocess.CalledProcessError:
        pass
    finally:
        return response


def _create_str_result(response: ResponseObject) -> str:
    response.str_result = format('[{ip}] pinged {n_times} times, min: {t_min:.2f}ms, avg: {t_avg:.2f}ms, max: {t_max:.2f}ms, {ppc:.0f}% Packet loss'.format(
        ip=response.ip, n_times=response.number_of_pings, t_min=response.time_min_ms,
        t_max=response.time_max_ms, t_avg=response.time_avg_ms, ppc=response.packets_lost_percentage))
    return response.str_result


def ping_linux(target: str, times: int) -> lib_shell.ShellCommandResponse:
    """
    >>> if lib_platform.is_platform_posix:
    ...     response = ping_linux(target='1.1.1.1', times=1)

    """
    try:
        response = ping_linux_ipv4(target=target, times=times)
    except subprocess.CalledProcessError:
        response = ping_linux_ipv6(target=target, times=times)
    return response


def ping_linux_ipv4(target: str, times: int) -> lib_shell.ShellCommandResponse:
    """
    >>> if lib_platform.is_platform_posix:
    ...     response = ping_linux_ipv4(target='1.1.1.1', times=1)
    ...     assert response.stdout is not None

    >>> if lib_platform.is_platform_posix:
    ...     response = ping_linux_ipv4(target='1.1.1.1', times=10)
    ...     assert response.stdout is not None


    """
    # ping -i parameter decimal sign can be different (0.2 or 0,2) on different linux versions
    reply_wait_deadline_seconds = int(5 + times * 0.2)
    try:
        cmd = 'ping -c {times} -W2000 -i 0.2 -w {deadline} {target}'.format(times=times, target=target, deadline=reply_wait_deadline_seconds)
        response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    except subprocess.CalledProcessError:
        cmd = 'ping -c {times} -W2000 -i 0,2 -w {deadline} {target}'.format(times=times, target=target, deadline=reply_wait_deadline_seconds)
        response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    return response


def ping_linux_ipv6(target: str, times: int) -> lib_shell.ShellCommandResponse:
    # ping -i parameter decimal sign can be different (0.2 or 0,2) on different linux versions
    reply_wait_deadline_seconds = int(5 + times * 0.2)
    try:
        cmd = 'ping -6 -c {times} -W2000 -i 0.2 -w {deadline} {target}'.format(times=times, target=target, deadline=reply_wait_deadline_seconds)
        response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    except subprocess.CalledProcessError:
        cmd = 'ping -6 -c {times} -W2000 -i 0,2 -w {deadline} {target}'.format(times=times, target=target, deadline=reply_wait_deadline_seconds)
        response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    return response


def ping_darwin(target: str, times: int) -> lib_shell.ShellCommandResponse:
    """
    >>> if lib_platform.is_platform_darwin:
    ...     response = ping_darwin(target='1.1.1.1', times=1)

    """
    try:
        response = ping_darwin_ipv4(target=target, times=times)
    except subprocess.CalledProcessError:
        response = ping_darwin_ipv6(target=target, times=times)
    return response


def ping_darwin_ipv4(target: str, times: int) -> lib_shell.ShellCommandResponse:
    """
    >>> if lib_platform.is_platform_darwin:
    ...     response = ping_darwin_ipv4(target='1.1.1.1', times=1)
    ...     assert response.stdout is not None

    >>> if lib_platform.is_platform_darwin:
    ...     response = ping_darwin_ipv4(target='1.1.1.1', times=10)
    ...     assert response.stdout is not None

    """
    # ping -i parameter decimal sign can be different (0.2 or 0,2) on different linux versions
    try:
        cmd = 'ping -c {times} -W2000 -i 0.2 {target}'.format(times=times, target=target)
        response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    except subprocess.CalledProcessError:
        cmd = 'ping -c {times} -W2000 -i 0,2 {target}'.format(times=times, target=target)
        response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    return response


def ping_darwin_ipv6(target: str, times: int) -> lib_shell.ShellCommandResponse:
    # ping -i parameter decimal sign can be different (0.2 or 0,2) on different linux versions
    try:
        cmd = 'ping -6 -c {times} -W2000 -i 0.2 {target}'.format(times=times, target=target)
        response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    except subprocess.CalledProcessError:
        cmd = 'ping -6 -c {times} -W2000 -i 0,2 {target}'.format(times=times, target=target)
        response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    return response


def ping_windows(target: str) -> lib_shell.ShellCommandResponse:
    """
    >>> if lib_platform.is_platform_windows:
    ...     response = ping_windows(target='1.1.1.1')
    """

    try:
        response = ping_windows_ipv4(target=target)
    except subprocess.CalledProcessError:
        response = ping_windows_ipv6(target=target)
    return response


def ping_windows_ipv4(target: str) -> lib_shell.ShellCommandResponse:
    cmd = 'ping -w 2000 ' + target
    response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    return response


def ping_windows_ipv6(target: str) -> lib_shell.ShellCommandResponse:
    cmd = 'ping -w 2000 ' + target
    response = lib_shell.run_shell_command(command=cmd, shell=True, log_settings=lib_shell.conf_lib_shell.log_settings_qquiet, retries=1)
    return response
