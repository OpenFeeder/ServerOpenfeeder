# coding: utf-8
#!/usr/bin/env python

# /* *****************************************************************************
#  * 
#  * _____________________________________________________________________________
#  *
#  *                    TCP PYTHON SERVER 
#  * _____________________________________________________________________________
#  *
#  * Titre            : mise en place d'un script serveur TCP multithreding
#  * Version          : v00
#  * Date de creation : 11/07/2019
#  * Auteur           : MMADI Anzilane
#  * Contact          : anzilan@hotmail.fr
#  * Web page         : 
#  * Collaborateur    : ...
#  * Processor        : ...
#  * Tools used       : a simple PC
#  * Compiler         : python
#  * Programmateur    : ...
#  * Note             : faire attention aux synchronisation des threads 
#  *******************************************************************************
#  *******************************************************************************
#  */

#--------------------------------> I M P O R T S <-----------------------------------------------------
from argparse import ArgumentParser
from threading import Lock, Thread
from socket import SO_REUSEADDR, SOCK_STREAM, socket, SOL_SOCKET, AF_INET
import sys
import select
import datetime
import os
import logging
import smtplib # mail services 

#--------------------------------> U S E R - I N P U T - H A N D L I N G <-------------------------------
# Initialize instance of an argument parser
server_parser = ArgumentParser(description='Multi-threaded TCP Server')

# Add optional argument, with given default values if user gives no arg
server_parser.add_argument('-p', '--port', default=8500, type=int, help='Port over which to connect')

server_parser.add_argument('-@', '--toaddrs', default='anzilan@hotmail.fr', help='the mail to notice Error')
# Get the arguments
server_args = server_parser.parse_args()

#--------------------------------> G L O B A L - V A R I A B L E S <-------------------------------------
log = None
server_ip = ''
server_counter = 0  #count number of client connected 
server_thread_lock = Lock()
server_smtp = smtplib.SMTP('smtp.gmail.com', 587)
#____________________________________________________
# Create a server TCP socket and allow address re-use
server_sock = socket(AF_INET, SOCK_STREAM)
server_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
server_sock.bind((server_ip, server_args.port))

#__________________________________________________________________________
# Create a list in which threads will be stored in order to be joined later
server_ClientConnceted = []

#--------------------------------> G L O B A L - F U N C T I O N S <-------------------------------------
def sendMail(subject, msgToSend) :
    #print "SEND MAILS : ", msgToSend
    toaddrs = [server_args.toaddrs]
    sujet = subject
    message = u"""%s\n\nOpenfeeder !!""" % (msgToSend)

    msg = """From: %s\r\nTo: %s\r\nSubject: %s\r\n \r\n%s""" % (fromaddr, ", ".join(toaddrs), sujet, message)
    # print msg
    try:
        server_smtp.sendmail(fromaddr, toaddrs, msg)
    except smtplib.SMTPException as e:
        print(e)
        return False
    log.info("MAIL SEND")
    return True

#--------------------------------> T H R E A D E D - S E R V E R - G E S T I O N - H A N D L E R <-------

class Server_GestionHundler(Thread):
    #Server Gestion definition
    # self    : curent prompt
    # lock    : to manage the scr shared
    def __init__(self, lock):
        Thread.__init__(self)
        self.lock = lock
        self.stop = True
        self.timeToClearClient = 23*60+50


    #________________________________________________________
    # Stop thread 
    def serverCmmandStopLoop(self) :
        with self.lock:
            self.stop = False
            print 'stop = ', self.stop
    
    def stopClentsConnected(self) :
        i = 0
        while not not server_ClientConnceted : #not empty
            if not server_ClientConnceted[i].clientSocketOpen() :
                if server_ClientConnceted[i].is_alive() :
                    server_ClientConnceted[i].join()
                    del server_ClientConnceted[i]
                    print "client ", i ," est arrete "
            else :
                print "client ", i ," est en cours d'execution "
                server_ClientConnceted[i].clientStopLoop()
            if len(server_ClientConnceted) > 0 :
                i = (i+1)%len(server_ClientConnceted)
                print "Aucun client n'est connecte ", len(server_ClientConnceted)    

    #_______________________________________________________
    # Server gestion 
    def run(self):
        print "COMMANDE TO MANAGE THE SERVER : \n"
        print "CMD h or H to print menu"
        print 'Enter CMD : '
        while self.stop : 
            input = select.select([sys.stdin], [], [], 1)[0]  # template to have a  keyboard listener
            if input:                                         # non bloking methode
                value = sys.stdin.readline().rstrip()
                # TODO : commande to manage the server 
                if value == "q" :
                    print 'Exit ----> \n (^ . ^)\n ()###()\n (") (")'
                    sys.exit(0)
                elif value == "h" or value == "H" :
                    print "COMMANDS HELP"
                    print "h : print command menu"
                    print "q : stop server"
                    print "x : clear clients connected"
                    print "s : send mail to test"
                elif value == "n" :
                    print "nb client connect : ", len(server_ClientConnceted)
                elif value == "x" :
                    self.stopClentsConnected()
                elif value == "s" : 
                    sendMail("Test", "je tests un mail")
                else:
                    print "You entered: %s" % value
                print 'Enter CMD : '
            else :
                #try to join of
                now = datetime.datetime.now()
                #erreur du premier test ici 
                if (now.hour*60+now.minute < self.timeToClearClient) :
                    #for all client connected try to stop 
                    for item in server_ClientConnceted :
                        if not item.clientSocketOpen():
                            if item.is_alive() :
                                item.join()
                            server_ClientConnceted.remove(item)
                else :
                    self.stopClentsConnected()
                            
    

       

#--------------------------------> T H R E A D E D - C L I E N T - H A N D L E R <-----------------------

class Server_ClientHandler(Thread):
    #client definition 
    # self    : curent client 
    # address : ip address of client connected 
    # port    : port of client connected  
    # lock    : to manage the scr shared between all clients 
    # stop    : to stop the loop of receive
    # socketOpened : say if socket is in state opened 
    # self.numSeq : num sequence for ack  
    def __init__(self, address, port, socket, lock):
        Thread.__init__(self)
        self.address = address
        self.port = port
        self.socket = socket
        self.lock = lock
        self.stop = True
        self.socketOpened = True
        self.idSite = 0
        self.numSeq = [0,0,0,0,0,0,0,0]

    def getInfos(self) :
        return "adress : "+str(self.address)+" port : "+str(self.port)+" id site : "+str(self.idSite)

    #________________________________________________________
    # socket openned 
    def clientSocketOpen(self) :
        return self.socketOpened
    
    #________________________________________________________
    # Stop thread 
    def clientStopLoop(self) :
        log.info(("Client : "+str(self.address)+" connected in port : "+ str(self.port)+" Closed"))
        with self.lock :
            self.socket.close()
            self.stop = False
            self.socketOpened = False
    
    #________________________________________________________
    # Send MSG
    def sendToMaster(self, msgToSend) :
        if self.socketOpened :
            return self.socket.send(msgToSend)
        else :
            return 0
            

    #________________________________________________________
    # Save on fils log fils 
    def saveOnFile(self, ind, station, dataToSave) :
        #create dir if dosen't exist 
        root = 'LogsOf/site'+str(station)
        fileNoExit = False
        arbre = root+'/OF'+str(ind)
        if (not os.path.isdir(root)) or (not os.path.isdir(arbre)):
            if os.system('mkdir -p '+arbre) : 
                print 'ERROR : create foloder '
                return False
            fileNoExit = True

        fileName = arbre+"/"+datetime.datetime.today().strftime('%Y-%m-%d')+".CSV"
        with open(fileName, "a") as fils:
            for l in dataToSave :
                if len(l) > 0 :
                    fils.write(l+"\n")
            log.info("Save on file : "+fileName+" ok !!")
            return True
        log.error("can't open file : "+fileName)
        return False
                

    #_______________________________________________________
    # pars data receive
    def parsDataRecive(self, dataToPars) : 
        # split between the header and data (infos)
        p1 = dataToPars.split('#')
        try :
            openfeederNum = int(p1[1])
            typeMsg = int(p1[2])
            station = int(p1[3])
            self.idSite = station #biensur penser à factoriser 
            numBloc = int(p1[4])
            log.info("openfeederNum : "+str(openfeederNum)+", typeMsg : "+str(typeMsg)+", station : "+str(station)+", numBloc : "+str(numBloc))
        except :
            log.debug("impossible de recuperer l'entete du paquet")
            return False     
        
        if typeMsg == 0: # error receive 
            with self.lock :
                # may be check if smtp server is connected 
                if not (sendMail("ERROR NOTIFICATION", p1[0])) : 
                    log.debug("MAIL Not Send :  ERROR NOTIFICATION")
                    return False
                log.info("ERROR NOTIFICATION Send")
                if openfeederNum != 254 : # is not the master  
                    log.error("Slave :"+str(openfeederNum)+" is in error state")
                else : 
                    log.error("The Master :"+str(openfeederNum)+" finished in error state")
            return True
        elif typeMsg == 1: # data 
            #split datas lines
            p2 = p1[0].split('\n')
            if self.numSeq[openfeederNum-1]+1 == numBloc:
                self.numSeq[openfeederNum-1] += 1
                self.saveOnFile(openfeederNum, station, p2)
                log.info("save ok !!")
                return True
            else :
                log.warning("bloc already receive")
                return True
        elif typeMsg == 2: #end collect 
            with self.lock :
                if not (sendMail("NOTIFICATION", p1[0])) :
                    log.debug("MAIL Not Send : NOTIFICATION") 
                self.socketOpened = False # close socket 
                log.info("NOTIFICATION Send")
            log.error("The Master :"+str(openfeederNum)+" finished normal in state")
        else :
            return False
        return True
    
                     
            
    
    #________________________________________________________
    # Define the actions the thread will execute when called.
    # self : curent client connected 
    def run(self):
        log.info(("Client : "+str(self.address)+" connected in port : "+str(self.port)))
        global server_counter #this parametre is using juste for the debug 
        clientInfo = "Client : "+str(self.address)+" connected in port : "+str(self.port)
        sendMail("Notification", str(clientInfo))
       # Lock the changing of the shared counter value to prevent erratic multithread changing behavior
        while self.stop :
            try :
                data = self.socket.recv(1024)
                if len(data) > 0 :
                    # Notify that data has been received
                    log.info(str(self.address)+":  msg received "+data+"\nsize : "+str(len(data)))
                    print self.address, ":  msg received size : ", len(data)
                    if self.parsDataRecive(data) :
                        self.socket.send("MSG RECEIVE "+str(len(data)))
                        if not self.socketOpened :
                            self.clientStopLoop()
            except :
                pass
            
       
#--------------------------------> M A I N - S E R V E R <---------------------------------------------- 

def main():
    global SGH, server_sock, server_thread_lock
    log.info("SERVER START........")
    #start promt, Server management 
    SGH = Server_GestionHundler(server_thread_lock)
    SGH.start()

    while 1:
        try: 
            # Listen for a request
            server_sock.listen(1)
            # Accept the request
            client_sock, client_addr = server_sock.accept()
            # Set Client socket in no bloking mode 
            client_sock.setblocking(0)
            # Spawn a new thread for the given request
            newClient = Server_ClientHandler(client_addr[0], client_addr[1], client_sock, server_thread_lock)
            newClient.start()
            server_ClientConnceted.append(newClient) # add the new client connected
        except KeyboardInterrupt:
            log.debug("SERVER STOP")
            break

    #___________________________________________________________________________________________________
    # When server ends gracefully (through user keyboard interrupt), wait until remaining threads finish
    for item in server_ClientConnceted:
        if item.is_alive():
            item.clientStopLoop()
            item.join()

    if SGH.is_alive() :
        SGH.serverCmmandStopLoop()
        SGH.join()
        log.info("SERVER HUNDLER STOP")

    #___________________________________________________________________________________________________
    # close SMTP Server 
    server_smtp.quit()
    log.info("SMTP SERVER STOP")

# Execution or import
if __name__ == "__main__":

    # Logging setup
    logging.basicConfig(filename='server.log', filemode='a', format="[%(asctime)s][%(module)s:%(funcName)s:%(lineno)d][%(levelname)s] %(message)s")
    log = logging.getLogger()

    print("\n[DBG] DEBUG mode activated ... ")
    log.setLevel(logging.DEBUG)
    # log.setLevel(logging.INFO)

    #____________________________________________________
    # init mail service 
    server_smtp.ehlo()
    server_smtp.starttls()
    server_smtp.login('openfeeder09@gmail.com', 'Openfeeder@09') #no safe
    fromaddr = 'openfeeder <openfeeder09@gmail.com>'
    log.info("SMTP SERVER START")

    # Start executing
    main()
