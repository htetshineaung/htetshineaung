#include "proto.h"

#include <string.h>

uint8_t proto_crc8(const uint8_t *data, size_t n) {
    uint8_t crc = 0;
    for (size_t i = 0; i < n; i++) {
        crc ^= data[i];
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
    }
    return crc;
}

size_t proto_encode(uint8_t *out, uint8_t type, const uint8_t *payload, uint8_t len) {
    if (len > PROTO_MAX_LEN) len = PROTO_MAX_LEN;
    out[0] = PROTO_SYNC;
    out[1] = type;
    out[2] = len;
    if (len) memcpy(out + 3, payload, len);
    out[3 + len] = proto_crc8(out + 1, (size_t)len + 2);
    return (size_t)len + 4;
}

void proto_rx_init(proto_rx_t *rx) { memset(rx, 0, sizeof *rx); }

enum { S_SYNC, S_TYPE, S_LEN, S_DATA, S_CRC };

bool proto_feed(proto_rx_t *rx, uint8_t b) {
    switch (rx->state) {
    case S_SYNC:
        if (b == PROTO_SYNC) rx->state = S_TYPE;
        return false;
    case S_TYPE:
        rx->type = b;
        rx->state = S_LEN;
        return false;
    case S_LEN:
        if (b > PROTO_MAX_LEN) { rx->bad++; rx->state = (b == PROTO_SYNC) ? S_TYPE : S_SYNC; return false; }
        rx->len = b;
        rx->idx = 0;
        rx->state = b ? S_DATA : S_CRC;
        return false;
    case S_DATA:
        rx->buf[rx->idx++] = b;
        if (rx->idx == rx->len) rx->state = S_CRC;
        return false;
    default: {                                   // S_CRC
        uint8_t hdr[2] = {rx->type, rx->len};
        uint8_t crc = proto_crc8(hdr, 2);
        for (uint8_t i = 0; i < rx->len; i++) {  // continue the CRC over the payload
            crc ^= rx->buf[i];
            for (int k = 0; k < 8; k++)
                crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
        }
        rx->state = S_SYNC;
        if (crc == b) return true;
        rx->bad++;
        return false;
    }
    }
}
