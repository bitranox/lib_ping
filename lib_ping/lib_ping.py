# STDLIB
import os
import re
import subprocess

# OWN
import lib_detect_encoding


class ResponseObject(object):
    def __init__(self) -> None:
        # init values for not reached condition
        self.target = ''
        self.reached: bool = False
        self.ip: str = '0.0.0.0'
        self.number_of_pings: int = 0
        self.time_min_ms: float = -1
        self.time_avg_ms: float = -1
        self.time_max_ms: float = -1
        self.n_packets_lost: int = 0
        self.packets_lost_percentage: int = 100
        self.str_result = ''


def ping(target: str, times: int = 4) -> ResponseObject:
    """

    >>> ping('www.google.com')  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    <...ResponseObject object at ...>

    >>> response = ping('1.1.1.1', 1)
    >>> response.reached
    True
    >>> response.packets_lost_percentage
    0

    """

    if os.name == 'nt':  # win32
        cmd = 'ping -w 2000 ' + target
    else:  # unix/linux
        cmd = 'ping -c {times} -W2000 -i 0.2 {target}'.format(times=times, target=target)

    response = ResponseObject()
    response.target = target
    response.number_of_pings = times

    # execute ping command and get stdin thru pipe
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]
    if not pipe:
        if os.name == 'nt':  # win32
            cmd = 'ping -w 2000 ' + target
        else:  # unix/linux
            cmd = 'ping -6 -c {times} -W2000 -i 0.2 {target}'.format(times=times, target=target)
        pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()[0]
        if not pipe:
            _create_str_result(response=response)
            return response

    # replace CR/LF
    encoding = lib_detect_encoding.detect_encoding(pipe)
    pipe = pipe.decode(encoding)
    text = pipe.replace('\r\n', '\n').replace('\r', '\n')

    # match IP address in format: [192.168.1.1] (192.168.1.1)
    ip = re.findall(r'(?<=[(\[])\d+\.\d+\.\d+\.\d+(?=[)\]])', text)
    if not ip:
        ip = re.findall(r'\d+\.\d+\.\d+\.\d+', text)
    response.ip = ip[0] if ip else '0.0.0.0'

    # avg ping time
    if os.name == 'nt':
        time = re.findall(r'(\d+(?=ms))+', text)
        if time:
            response.time_avg_ms = float(time[len(time) - 1])
            response.time_max_ms = float(time[len(time) - 2])
            response.time_min_ms = float(time[len(time) - 3])
    else:
        time = re.findall(r'(?=\d+\.\d+/)(\d+\.\d+)+', text)
        if time:
            response.time_min_ms = float(time[0])
            response.time_avg_ms = float(time[1])
            response.time_max_ms = float(time[2])
    if not time:
        response.time_min_ms = response.time_avg_ms = response.time_max_ms = -1

    # packet loss rate
    lost = re.findall(r'\d+.\d+(?=%)', text)
    if not lost:
        lost = re.findall(r'\d+(?=%)', text)

    response.n_packets_lost = len(lost)
    response.packets_lost_percentage = int(round(float(lost[len(lost) - 1]))) if lost else 100
    if response.packets_lost_percentage < 100:
        response.reached = True
    _create_str_result(response=response)
    return response


def _create_str_result(response: ResponseObject) -> str:
    response.str_result = format('[{ip}] pinged {n_times} times, min: {t_min:.2f}ms, avg: {t_avg:.2f}ms, max: {t_min:.2f}ms, {ppc:.0f}% Packet loss'.format(
        ip=response.ip, n_times=response.number_of_pings, t_min=response.time_min_ms,
        t_max=response.time_max_ms, t_avg=response.time_avg_ms, ppc=response.packets_lost_percentage))
    return response.str_result
