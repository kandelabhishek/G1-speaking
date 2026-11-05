import socket
import time
import struct
import wave


def receive_g1(seconds):
    #recieves g1 microphone audio
    #return the collected raw PCM bytes
    MCAST_GRP = '239.168.123.161'  #listining to the channel 239.168.123.161 in port 5555
    PORT = 5555

    ROBOT_IP = '192.168.123.164' 

    #check an IPv4 socket
    #It builds the reciever. socket.AF_INET means it uses standard IPv4 address. 
    # SOCK_DGRAM and IPPROTO_UDP mean it uses user datagram protocol.
    #It tells the operating system to create a new network endpoint that can send or recieve data.
    #socket.AF_INET -> the address family.It tells it to use standard IPv4 address.
    #socket.SOCK_DGRAM -> this is the socket type.  It tells the socket to use Datagrams. 
    #Datagrams : Datagrams are individual, connectionless packets of data used by UDP, rather then continous, verified stream of data which the TCP uses.
    #socket.IPPROTO_UDP-> It is the protocol. This esplicitly forces the oscket to use the UDP protocol for transmitting those datagrams.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) 

    #Allow the port ot be reused
    #If the script crashes and we try to run it again, then the os might still think the port is locked. 
    #This like let us to reuse the port instatly.
    #sock.setsockopt()-> changes the internal configuration settings of socket
    #socket.SOL__SOCKET-> this specifies that the setting we want to change applies to the socket level itself.
    #socket.SO_ReUSEADDR -> This stands for 'The Socket Option: Reuse Address'. By default, when the program closes or crashes, 
    # the operating system locks the network prot for few minutes to ensure all delayed packets finish arriving. 
    #this options override that clock
    #1 -> enable, 0 -> disable
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


    #This creates an empty bucket (bytearray) where we will dump the incoming data chunks as they arrive
    collected_deta = bytearray()

    try:
        #Bind it to port
        #it tells the socket to activally listen to the port 5555
        sock.bind(("", PORT))


        #join the multicast group using the specific network interface
        #translates the Ip address to low level binary commadn that tell the computer's operating system to join multicast
        #Our computer system's stack cannot read python string.it requires 8-byte data structure called ip_mreq.
        #socket.inet_aton-> inet_aton stands for Internet Address to Network. It takes our ip string and squishes it exactly 4 bytes of binary data
        #socket.iet_aton(ROBOT_IP)-> This does the exact thing to our PC ip address.
        #struct.pack('4s4s'....)-> The struct library creates C-style data structures in python. The format string '4s4s' tellls python"Take the first 4-byte string and glue the second 4-byte string directly to the end of it"
        #for example 239.168.123.161 . It gets converted into a 4-byte string. we can visualize it like [239][168][123][161]
        mreq = struct.pack('4s4s', socket.inet_aton(MCAST_GRP), socket.inet_aton(ROBOT_IP))
     
        #set.IPPROTO_IP -> the option level. This tells the system to apply this setting one layer depper. directly to the ip layer of network stack.
        #socket.IP_ADD_MEMBERSHIP -> This is the official command telling your operating system's kernel to send an IGMP(Internet Group Management protocol) message to the network router saying "Start routing packets for this multicast froup to my machine"
        #mreq-> The option value. This is the 8-byte package that we created. It acts as the payload for the IP_ADD_MEMBERSHIP.
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        #set timeout so the loop doest block forever
        #If no data arrives within 1/19th of a second, the socket will throw an error instead of freezin gthe program forever.

        sock.settimeout(0.1)

        #time.monotonic() records the exact starting tie using a system clock that cannot be trhown off by daylight saving time or sync updates
        #recieve packats and collect them
        start_time = time.monotonic()

        #This loop continously, constantly checking the current time against the start_time.
        #once the difference is greater then requested seconds, the loop stops.
        while(time.monotonic()-start_time)<seconds:
            try:
                #rsock.recv(4096) bytes of incoming data at once.
                #extend(packet) dumps that data into the bucket.
                #If the 0.1 second timeut passes without the data, the except block catches the error and tells the loop to continue.
                #set buffer size of 4090 bytes per packet
                packet = sock.recv(65535) #4096
                collected_deta.extend(packet)

            except socket.timeout:
                #if no data is connected in 0.1 secends, continue to check time
                continue
            
            
            #this converts the byterrary bucket into locked,read-only bytes.
            #byterrary ->  it is essentialy a specialized, expandable bucket where you can continously dump incoming network data.
                       
        return bytes(collected_deta)

    finally:
        #close the socket even if the loop crashes
                
         sock.close() 

        
# if __name__ == "__main__":
#     try:
#         audio = receive_g1(10)

#         print("Received bytes:", len(audio))
#         print("Audio duration:", len(audio) / 32000, "seconds")

#     except KeyboardInterrupt:
#         print("\nRecording stopped.")

#     except OSError as error:
#         print("Error:", error)
        

# with wave.open("g1_test.wav", "wb") as output:
#     output.setnchannels(1)
#     output.setsampwidth(2)
#     output.setframerate(16000)
#     output.writeframes(audio)

# print("Saved recording to g1_test.wav")



