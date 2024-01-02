import json
import socket
import threading
import time
import cv2 as cv
import numpy as np
import gzip
import base64
import vs_utils as vs
import struct


def broadcasting(addr, broad_client_socket):
    global var
    try:
        print('CLIENT {} CONNECTED!'.format(addr))
        if broad_client_socket:

            server_status = {
                "response": "running",
                "streamingmode": "broadcasting",
                "nclients": 3,
                "handover": "yes"
            }
            json_msg = json.dumps(server_status)
            message = struct.pack("Q", len(json_msg)) + json_msg.encode()
            broad_client_socket.sendall(message)

            data = b""
            payload_size = struct.calcsize("Q")

            while True:
                while (len(data)) < payload_size:
                    packet = broad_client_socket.recv(4 * 1024)
                    if packet:
                        data += packet
                    else:
                        break

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]

                while len(data) < msg_size:
                    data += broad_client_socket.recv(4 * 1024)

                frame_data = data[:msg_size]
                data = data[msg_size:]

                resp = json.loads(frame_data.decode())
                if resp['request'] == 'streamstart':
                    print('streamstart, addr({})'.format(addr))
                    start_streaming = {"response": "streamstarting"}
                    json_msg = json.dumps(start_streaming)
                    message = struct.pack("Q", len(json_msg)) + json_msg.encode()
                    broad_client_socket.sendall(message)

                    print("Sending image")
                    while True:
                        json_msg = json.dumps(var)
                        message = struct.pack("Q", len(json_msg)) + json_msg.encode()
                        broad_client_socket.sendall(message)
                        time.sleep(0.05)



    except Exception as e:
        print(e)
        print(f"CLIENT {addr} DISCONNECTED")
        pass


def carriar(request, port=9191):
    global var
    Host = "127.0.0.1"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as clint_side:
        clint_side.connect((Host, port))
        data = b""
        payload_size = struct.calcsize("Q")

        while True:
            while (len(data)) < payload_size:
                packet = clint_side.recv(4 * 1024)
                if packet:
                    data += packet
                else:
                    break

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data) < msg_size:
                data += clint_side.recv(4 * 1024)

            frame_data = data[:msg_size]
            data = data[msg_size:]

            var = json.loads(frame_data.decode())

            if 'img' in var:
                encoded_base64_image = var['img'].encode()
                # Remove the base64 encoding
                decoded_base64_image = base64.b64decode(encoded_base64_image)
                # Decompress the image data
                decompressed_image = gzip.decompress(decoded_base64_image)
                # Convert the raw bytes to make a frame (type is ndarray)
                frm = np.frombuffer(decompressed_image, dtype='uint8')
                # Reshare the ndarray of frame properly e.g. 320 by 240, 3 bytes
                frm = frm.reshape(vs.RESOLUTION_HEIGHT, vs.RESOLUTION_WIDTH, vs.BYTES_PER_PIXEL)

                cv.imshow('Client 3', frm) # CHANGE this for another client


                if cv.waitKey(1) == ord('q'):
                    clint_side.close()
                    quit(0)

            elif var['response'] == 'running':
                print('server running')
                json_msg = json.dumps(request)
                message = struct.pack("Q", len(json_msg)) + json_msg.encode()
                clint_side.sendall(message)
            elif var['response'] == 'streamstarting':
                print('Streaming')
            elif var['response'] == 'overloaded':
                print("Streams are overloaded")
                if len(var['ports']) > 0:
                    print('Available ports:', var['ports'])
                    port = int(input("Choose one port"))
                    if port in var['ports']:
                        request = {"request": "streamstart", 'mode': 'carriar'}
                        carriar(request, port)
                    else:
                        print("Quitting...")
                        clint_side.close()
                        quit(0)
                else:
                    print("Quitting...")
                    clint_side.close()
                    quit(0)




if __name__ == "__main__":
    global var
    var = None
    inp = int(input("press [1] to carriar and [2] to broadcast"))
    if inp == 1:
        request = {"request": "streamstart", 'mode': 'carriar'}
        carriar(request)
    elif inp == 2:
        Host = "0.0.0.0"
        port = 9194  # CHANGE this for another client
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        broadcast_socket.bind((Host, port))
        broadcast_socket.listen(3)
        socket_address = (Host, port)
        print("Listening at", socket_address)

        request = {"request": "streamstart", "mode": "broadcasting", "port": port}
        # to listen and show from server
        thread = threading.Thread(target=carriar, args=(request,))
        thread.start()

        while True:
                broad_client_socket, addr = broadcast_socket.accept()
                thread = threading.Thread(target=broadcasting, args=(addr, broad_client_socket))
                thread.start()

