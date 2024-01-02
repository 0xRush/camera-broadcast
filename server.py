import socket
import threading
import time
import cv2 as cv
import numpy as np
import gzip
import base64
import vs_utils as vs
import json
import struct

def start_stream(fonORbac):
    global frame

    while True:
        while True:
            cap = cv.VideoCapture(fonORbac)
            if not cap.isOpened():
                print("Cannot open camera")
                exit()

            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Can't receive frame (stream end?). Exiting ...")
                    break
                # Make a resolution of 320 by 240 pixels. 3 bytes per pixel
                resized_frame = cv.resize(frame, (vs.RESOLUTION_WIDTH, vs.RESOLUTION_HEIGHT))
                # Get the raw bytes of the frame
                raw_image_bytes = resized_frame.tobytes()
                # Compress the frame(image) using GZIP algorithm
                compressed_image = gzip.compress(raw_image_bytes)
                # Encode to Base64
                encoded_base64_image = base64.b64encode(compressed_image)
                image_str = encoded_base64_image.decode()
                encoded_base64_image = image_str.encode()
                # Remove the base64 encoding
                decoded_base64_image = base64.b64decode(encoded_base64_image)
                # Decompress the image data
                decompressed_image = gzip.decompress(decoded_base64_image)
                # Convert the raw bytes to make a frame (type is ndarray)
                frm = np.frombuffer(decompressed_image, dtype='uint8')
                # Reshare the ndarray of frame properly e.g. 320 by 240, 3 bytes
                frm = frm.reshape(vs.RESOLUTION_HEIGHT, vs.RESOLUTION_WIDTH, vs.BYTES_PER_PIXEL)
                cv.imshow('Server', frm)
                # To quit, press q
                key = cv.waitKey(1) & 0xFF
                if key == ord('q'):
                    quit(0)
            # When everything done, release the capture
            cap.release()
            cv.destroyAllWindows()


def serve_client(addr, client_socket, server_status):
    global frame
    global ports

    try:
        print('CLIENT {} CONNECTED!'.format(addr))
        if client_socket:

            json_msg = json.dumps(server_status)
            message = struct.pack("Q", len(json_msg)) + json_msg.encode()
            client_socket.sendall(message)

            data = b""
            payload_size = struct.calcsize("Q")

            while True:
                while (len(data)) < payload_size:
                    packet = client_socket.recv(4 * 1024)
                    if packet:
                        data += packet
                    else:
                        break

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]

                while len(data) < msg_size:
                    data += client_socket.recv(4 * 1024)

                frame_data = data[:msg_size]
                data = data[msg_size:]

                resp = json.loads(frame_data.decode())

                if resp['request'] == 'streamstart' and resp['mode'] == "carriar":
                    print('streamstart, addr({})'.format(addr))
                    start_streaming = {"response": "streamstarting"}
                    json_msg = json.dumps(start_streaming)
                    message = struct.pack("Q", len(json_msg)) + json_msg.encode()
                    client_socket.sendall(message)
                    print('message sent, start sending frames')

                    while True:
                        resized_frame = cv.resize(frame, (vs.RESOLUTION_WIDTH, vs.RESOLUTION_HEIGHT))
                        raw_image_bytes = resized_frame.tobytes()
                        compressed_image = gzip.compress(raw_image_bytes)
                        encoded_base64_image = base64.b64encode(compressed_image)
                        image_str = encoded_base64_image.decode()
                        img_dict = {"img": image_str}
                        json_msg = json.dumps(img_dict)
                        message = struct.pack("Q", len(json_msg)) + json_msg.encode()
                        client_socket.sendall(message)
                        time.sleep(0.05)
                elif resp['request'] == 'streamstart' and resp['mode'] == 'broadcasting':
                    print("new port", resp['port'])
                    ports.append(resp['port'])

                    print('streamstart, addr({})'.format(addr))
                    start_streaming = {"response": "streamstarting"}
                    json_msg = json.dumps(start_streaming)
                    message = struct.pack("Q", len(json_msg)) + json_msg.encode()
                    client_socket.sendall(message)
                    print('message sent, start sending frames')

                    while True:
                        resized_frame = cv.resize(frame, (vs.RESOLUTION_WIDTH, vs.RESOLUTION_HEIGHT))
                        raw_image_bytes = resized_frame.tobytes()
                        compressed_image = gzip.compress(raw_image_bytes)
                        encoded_base64_image = base64.b64encode(compressed_image)
                        image_str = encoded_base64_image.decode()
                        img_dict = {"img": image_str}
                        json_msg = json.dumps(img_dict)
                        message = struct.pack("Q", len(json_msg)) + json_msg.encode()
                        client_socket.sendall(message)
                        time.sleep(0.05)
                else:
                    json_msg = json.dumps(server_status)
                    message = struct.pack("Q", len(json_msg)) + json_msg.encode()
                    client_socket.sendall(message)

    except Exception as e:
        print(e)
        print(f"CLIENT {addr} DISCONNECTED")
        pass





Host = "0.0.0.0"
port = 9191
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((Host, port))
server_socket.listen(3)
socket_address = (Host, port)
print("Listening at", socket_address)
global frame
global ports
frame = None
ports = []

inp = int(input("share your camera press [1] or share a video press [2]"))
if inp == 1:
    inp2 = int(input("front camera press [0] back camera press [1]"))
    thread = threading.Thread(target=start_stream, args=(inp2,))
    thread.start()
elif inp == 2:
    inp3 = input("put the path of the video")
    thread = threading.Thread(target=start_stream, args=(inp3,))
    thread.start()

while True:
    if (threading.active_count() - 2) < 3:
        client_socket, addr = server_socket.accept()
        server_status = {
            "response": "running",
            "streamingmode": "broadcasting",
            "nclients": 3,
            "handover": "yes"
        }

        thread = threading.Thread(target=serve_client, args=(addr, client_socket, server_status))
        thread.start()
        print("TOTAL CLIENTS {}".format(threading.active_count() - 2))
    else:
        client_socket, addr = server_socket.accept()
        server_status = {"response": "overloaded", 'ports': ports}
        thread = threading.Thread(target=serve_client, args=(addr, client_socket, server_status))
        thread.start()
        print("\nTOTAL CLIENTS NUMBER CANNOT BE EXTENDED\n")
        print('Available ports: ', ports)

