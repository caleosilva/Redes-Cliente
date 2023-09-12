import socket
import json
from config import socket_host, socket_port, socket_rfid_client_host, socket_rfid_client_port

carrinho = []
codigoDoCaixa = ''

def enviar_ID_manualmente(client_server_socket):
    inputData = input('ID -> ')

    if (inputData == ''):
        print("ID inválido!\n")
    else:
        inputDataDict = {'header':'id', 'body': inputData, 'codigoDoCaixa': codigoDoCaixa}
        dataRcv = send_receive_data(client_server_socket, inputDataDict)
        return dataRcv

def send_receive_data(socket, data):
    serialized_data = json.dumps(data)
    data_size = len(serialized_data)
    
    socket.send(str(data_size).encode())  # Envia o tamanho dos dados
    
    ack = socket.recv(1024)  # Espera por um ack do servidor
    if ack.decode() == 'OK':
        socket.sendall(serialized_data.encode())
        return socket.recv(1024).decode('utf-8')

def mostrar_carrinho():
    total_itens = len(carrinho)
    valor_total = 0
    if total_itens > 0:
        print('\n-=-=-= CARRINHO =-=-=-')
        for item in carrinho:
            print(f"[{item['chave']}] {item['nome']} (R$ {item['preco']}): {item['quantidade']} unidades")
            valor_total += item['preco'] * item['quantidade']
        print(f"\nPreço total: R$ {valor_total:.2f}")
    else:
        print("\nO carrinho está vazio.")

def adicionar_produto_carrinho(produto):
    if produto == "204":
        pass
    else:
        data_dict = json.loads(produto)
        for chave, valor in data_dict.items():
            if valor['quantidade'] > 0:
                produto_encontrado = False
                for item in carrinho:
                    if item['chave'] == chave:
                        if item['quantidade'] < valor['quantidade']:
                            item['quantidade'] += 1
                            print(f"\nO produto '{valor['nome']}' foi adicionado ao carrinho.")
                        else:
                            print(f"\nLimite de estoque atingido para o produto '{valor['nome']}' no carrinho.")
                        produto_encontrado = True
                        break

                if not produto_encontrado:
                    carrinho.append({
                        'chave': chave,
                        'nome': valor['nome'],
                        'preco': valor['preco'],
                        'quantidade': 1
                    })
                    print(f"\nO produto '{valor['nome']}' foi adicionado ao carrinho.")

            else:
                print(f'\nO produto {valor["nome"]} não tem estoque!')

def comunicacao_socket(rfid_socket, client_server_socket):
    try:
        while True:
            dados_recebidos = rfid_socket.recv(1024).decode()
            data = json.loads(dados_recebidos)

            if data:
                if (data['header'] == 'comprar'):
                    data['body'] = carrinho
                    data = send_receive_data(client_server_socket, data)
                    rfid_socket.send('compra finalizada'.encode('utf-8'))
                elif (data['header'] == 'id'):
                    produtoInfo = send_receive_data(client_server_socket, data)

                    adicionar_produto_carrinho(produtoInfo)
                    rfid_socket.send(produtoInfo.encode('utf-8'))

            mostrar_carrinho()
    except socket.error as e:
        print("Erro de soquete:", e)
        rfid_socket.close()  # Fechar o socket em caso de erro
        client_server_socket.close()  # Fechar o socket em caso de erro
    except KeyboardInterrupt:
        print("Cliente interrompido pelo usuário.")
        rfid_socket.close()  # Fechar o socket em caso de interrupção
        client_server_socket.close()

def solicitar_tags_RFID():
    try:
        rfid_caixa_socket = socket.socket()
        rfid_caixa_socket.connect((socket_rfid_client_host, socket_rfid_client_port))
        dadosRcv = rfid_caixa_socket.recv(1024).decode()
        return json.loads(dadosRcv)
    except socket.error as e:
        print("\nNão foi possível se conectar com o RFID.")
        return []

def realizar_compra(client_server_socket):
    inputDataDict = {'header':'comprar', 'body': carrinho}
    dataRcv = send_receive_data(client_server_socket, inputDataDict)
    return dataRcv

def visualizarCaixas(client_server_socket):
    inputDataDict = {'header':'caixas', 'body': ''}
    dataRcv = send_receive_data(client_server_socket, inputDataDict)
    dataRcvJSON = json.loads(dataRcv)

    print("\n\n-=-=-= ESTADO DOS CAIXAS =-=-=-")
    print("\n CÓDIGO     STATUS\n")
    for chave, valor in dataRcvJSON.items():
        ativo = valor['ativo']
        if (ativo):
            print(f"[{chave}] -> Ocupado")
        else:
            print(f"[{chave}] -> Livre")

def menu(client_server_socket):

    menuInicial = True
    while menuInicial:
        print(f'\n\n-=-=-=-= MENU =-=-=-=-')
        print('[1] -> Iniciar nova compra')
        print('[2] -> Encerrar caixa')

        escolhaMenuInicial = input('\nOpção -> ')

        if (escolhaMenuInicial == '1'):
            continuar = True
            while continuar:
                print(f'\n\n-=-=-=-= MENU COMPRAS =-=-=-=-')
                print('[1] -> Inserir código manualmente')
                print('[2] -> Ler RFID')
                print('[3] -> Visualizar carrinho')
                print('[4] -> Finalizar compra')
                print('[5] -> Cancelar')

                escolha = input('\nOpção -> ')

                if (escolha == '1'):
                    produtoID = enviar_ID_manualmente(client_server_socket)
                    if(produtoID != 'False'):
                        adicionar_produto_carrinho(produtoID)
                    else:
                        print("O caixa está bloqueado!")
                elif (escolha == '2'):
                    listaRFID = solicitar_tags_RFID()
                    if(len(listaRFID) > 0):
                        for id in listaRFID:
                            inputDataDict = {'header':'id', 'body': id, 'codigoDoCaixa': codigoDoCaixa}
                            dataRcv = send_receive_data(client_server_socket, inputDataDict)
                            if(dataRcv != 'False'):
                                adicionar_produto_carrinho(dataRcv)
                            else:
                                print("O caixa está bloqueado!")
                                break
                elif (escolha == '3'):
                    mostrar_carrinho()
                elif (escolha == '4'):
                    if (len(carrinho) > 0):
                        resposta = realizar_compra(client_server_socket)
                        if (resposta == "201"):
                            print("\nCompra finalizada com sucesso!")
                            continuar = False
                    else:
                        print("Carrinho vazio")
                elif (escolha == '5'):
                    inputDataDict = {'header':'limparCaixa', 'body': ''}
                    dataRcv = send_receive_data(client_server_socket, inputDataDict)
                    continuar = False
                else:
                    print('\nOpção inválida!')
        elif (escolhaMenuInicial == '2'):
            return 'Encerrar'
    
def acessarCaixa(client_server_socket):
    global codigoDoCaixa
    inputData = input("\nCódigo do caixa -> ")

    if (inputData != ''):
        inputDataDict = {'header':'caixas', 'body': inputData, 'operacao': 'ocuparCaixa'}
        dataRcv = send_receive_data(client_server_socket, inputDataDict)
        dataRcvJSON = json.loads(dataRcv)
        
        if (dataRcvJSON == 204):
            print("\nCaixa não encontrado!")
        else:
            if(dataRcvJSON[inputData]['ativo']):
                print("\nCaixa em questão está em uso.")
            else:
                codigoDoCaixa = inputData
                result = menu(client_server_socket)
                return result
    else:
        print("\nCódigo inválido!")

def iniciarCaixa(client_server_socket):
    home = True
    while home:
        print(f'\n\n-=-=-=-= HOME =-=-=-=-')
        print('[1] -> Visualizar caixas')
        print('[2] -> Inserir o código do caixa')
        print('[3] -> Sair')

        escolha = input('\nOpção -> ')

        if (escolha == '1'):
            visualizarCaixas(client_server_socket)
        elif (escolha == '2'):
            data = acessarCaixa(client_server_socket)
            if (data == 'Encerrar'):
                return
        elif (escolha == '3'):
            home = False

def main():
    caixa_controller_socket = socket.socket()
    try:
        caixa_controller_socket.connect((socket_host, socket_port))
        print("Conectado ao caixa_controller_socket em", socket_host, "porta", socket_port)

        iniciarCaixa(caixa_controller_socket)
    except socket.error as e:
        print("Erro de conexão:", e)
    

if __name__ == "__main__":
    main()