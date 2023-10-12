import cv2
import numpy as np
import time
from py_openshowvar import openshowvar
import re
import serial.tools.list_ports


# PORT = "/dev/ttyUSB0" # TTL converter
PORT = "/dev/tty.usbserial-A904QEI2"  # TTL converter


# ---------------------------    serial PORT: python -> arduino     ----------------------------------------------
ser = serial.Serial(PORT)
ser.baudrate = 9600

# Definindo a posição do texto na imagem
posicao = (50, 50)  # coordenadas (x, y)

# Definindo a fonte, tamanho da fonte e cor do texto
fonte = cv2.FONT_HERSHEY_SIMPLEX
tamanho_fonte = 1.2
cor = (0, 0, 255)

u_x = 0
u_z = 0


#  Function to send tada to arduino
def serial_send(data):
    data = data.encode('ascii')
    print(data)
    ser.write(data)
    # time.sleep(0.05)


client = openshowvar('10.103.16.242', 7000)
client.can_connect

px2mm = 1.21794872 # pixel to millimeter constant IMPORTANT: defined based on the measured distance between the robot and the target

# ----------- define and move KUKA to the initial condiitons -------------
client.write('$OV_PRO', '42', debug=True)  # sets the speed 

x_robo = 300
y_default = 170 # the robot moves in the plane xz, so the y variable is a constant
z = 200

A = 180
B = 20
C = -180


# Defines the vaiable type to E6POS and the movment to PTP
client.write('COM_ACTION', '3', debug=True)
client.write("COM_POS", str("{X " + str(x_robo) + ", Y " + str(y_default) + ", Z " + str(z) + ", A " +
             str(A) + ", B " + str(B) + ", C " + str(C) + "}"), debug=False)  # Defines join angles
client.write('COM_ACTION', '3', debug=True)
client.write("COM_POS", str("{X " + str(x_robo) + ", Y " + str(y_default) + ", Z " + str(z) + ", A " +
             str(A) + ", B " + str(B) + ", C " + str(C) + "}"), debug=False)  # Defines join angles

quad_division_z = 200  # z limit that devides quadrants 1 and 2




# -------- KUKA physical limits ---------------
# OBS: this values were all measured for the SPECIFIC setup (orientation of the target,...)

# quadrant 1 limits
q1_x_max = 600
q1_x_min = 200
q1_z_max = 550
q1_z_min = 200

# quadrant 2 limits
q2_x_max = 600
q2_x_min = 60
q2_z_max = 200
q2_z_min = 30

# ------ vision initial condiitons ---------
videoCapture = cv2.VideoCapture(0)
prevCircle = (0, 0)
prevCirclePrev = (0, 0)
last_pos = None


# ---------- control filters variables ----------
error = 0    # Erro cumulativo inicial
error_dot_x = 0
error_dot_z = 0
error_dot_x_last = 0
error_dot_z_last = 0
error_x_last = 0
error_z_last = 0

error_x = 0
error_z = 0


current_error_anterior = 0

last_time = time.time()

# Define o intervalo desejado
lower_red = np.array([0, 100, 100])
upper_red = np.array([200, 255, 255])

# Definindo variáveis para o cálculo do erro cumulativo
alpha = 0.3  # Fator de correção do erro cumulativo

# scale_factor = 30/330
scale_factor = 60/330

next_pos = (0, 0)

x_filt = 0
y_filt = 0

new_x = 0
new_y = 0

x_filt_rast = 0
y_filt_rast = 0

pos_test_x_ant = 0
pos_test_y_ant = 0

pos_test_x_ant_rast = 0
pos_test_y_ant_rast = 0

# Define a direção do vetor (x, y)
direction = (1, 0)

# 5hz
a_est = 0.2391
b_est = 0.5219

# 2hz
a_rast = 0.2391
b_rast = 0.5219

max_trail_length = 50  # Comprimento máximo do rastro
center_trail_rast = []
center_trail_est = []

not_control = True
counter_control = 0

velocity = [0, 0]


def draw_cross(img, center, radius, color, thickness):
    x, y = center
    # Desenha a primeira linha da cruz
    cv2.line(img, (x - radius, y), (x + radius, y), color, thickness)
    # Desenha a segunda linha da cruz
    cv2.line(img, (x, y - radius), (x, y + radius), color, thickness)

# Função para desenhar uma seta


def draw_arrow(img, start, end, color, thickness):
    cv2.arrowedLine(img, start, end, color, thickness)


tiros = 6 # number of shots allowed

while True:
    ret, frame2 = videoCapture.read()
    if not ret:
        break

    frame = cv2.flip(frame2, 0)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Aplica o filtro de range na imagem
    mask = cv2.inRange(hsv, lower_red, upper_red)

    # Encontra o contorno do objeto filtrado
    contours, hierarchy = cv2.findContours(
        mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Encontra o centro do contorno e desenha um círculo vermelho
    if len(contours) > 0:
        c = max(contours, key=cv2.contourArea)
        (x, y), radius = cv2.minEnclosingCircle(c)
        center = (int(x), int(y))
        radius = int(radius)
        cv2.circle(frame, center, radius, (0, 255, 0), 3)
        draw_cross(frame, center, radius, (0, 0, 255), 10)

        if last_pos is not None:
            current_time = time.time()
            time_diff = current_time - last_time

            pos_test_x_rast = x
            pos_test_y_rast = y

            # low pass filter for position
            x_filt_rast = x_filt_rast*b_rast + pos_test_x_rast * \
                a_rast + pos_test_x_ant_rast*a_rast
            y_filt_rast = y_filt_rast*b_rast + pos_test_y_rast * \
                a_rast + pos_test_y_ant_rast*a_rast

            pos_test_x_ant_rast = pos_test_x_rast
            pos_test_y_ant_rast = pos_test_y_rast

            new_x = x_filt_rast
            new_y = y_filt_rast

            # Calculates position based on speed and the scale factor
            velocity = [(new_x - last_pos[0])/time_diff,
                        (new_y - last_pos[1])/time_diff]

            scale_factor_x = abs(velocity[0]*scale_factor)
            scale_factor_y = abs(velocity[1]*scale_factor)

            # print(scale_factor_x, scale_factor_y)

            next_pos = (int(new_x + scale_factor_x * velocity[0]*time_diff),
                        int(new_y + scale_factor_y * velocity[1]*time_diff))

            pos_test_x = next_pos[0]
            pos_test_y = next_pos[1]

            # Low pass filter for position
            x_filt = x_filt*b_est + pos_test_x*a_est + pos_test_x_ant*a_est
            y_filt = y_filt*b_est + pos_test_y*a_est + pos_test_y_ant*a_est

            pos_test_x_ant = pos_test_x
            pos_test_y_ant = pos_test_y

            next_pos = (int(x_filt), int(y_filt))

            x_robo = (next_pos[0] - 759 + 40)*px2mm
            z = (next_pos[1] - 341)*px2mm

            bla = client.read("$POS_ACT", debug=False)
            # # Extrair o conteúdo entre aspas simples
            # # Converter os bytes para string

            data_string = bla.decode()

            # Extrair os valores de X, Y e Z usando expressões regulares
            x_value = float(re.findall(r'X ([\d.-]+)', data_string)[0])
            y_value = float(re.findall(r'Y ([\d.-]+)', data_string)[0])
            z_value = float(re.findall(r'Z ([\d.-]+)', data_string)[0])

            # print("Valor de X do robo:", x_value)
            # print("Valor de Y do robo:", y_value)
            # print("Valor de Z do robo:", z_value)

            # print("Valor de X estimado:", x_robo)
            # print("Valor de Z estimado:", z)

            # print("Erro em x", (x_robo - x_value))
            # print("Erro em z", (z - z_value))

            error_x = (x_robo - x_value)
            error_z = (z - z_value)

            print(error_x, error_z)

            error_dot_x = -(error_x_last - error_x)/time_diff
            error_x_last = error_x

            error_dot_z = -(error_z_last - error_z)/time_diff
            error_z_last = error_z

            if (not_control):

                x_robot = x_robo
                z_robot = z

                counter_control += 1
                if (counter_control > 90):
                    not_control = False

            else:
                # print("TEM CONTROLE")
                kp_x = 0.5
                kp_z = 0.5

                kd_x = 0
                kd_z = 0

                u_x = error_x * kp_x + error_dot_x*kd_x
                u_z = error_z * kp_z + error_dot_z*kd_z

                if (u_x > 90):
                    u_x = 0

                if (u_x < -90):
                    u_x = -0

                if (u_z > 90):
                    u_z = 0

                if (u_z < -90):
                    u_z = -0

                if (abs(error_x) < 15 and abs(error_z) < 15):
                    x_robot = x_robo + u_x/1.05
                    z_robot = z + u_z/1.05
                else:
                    x_robot = x_robo + u_x
                    z_robot = z + u_z

            # --------------- shot logic ------------------------------
            if (abs((x - 759 + 40)*px2mm - x_value) < 15 and abs((y - 341)*px2mm - z_value) < 15):  #shot condition
                if (tiros > 1):
                    serial_send('b') # Shot 
                    serial_send('a') # Reload
                    time.sleep(0.05)
                    tiros = tiros - 1 # Compute number os shots left

            if (abs(error_x) > 100 or abs(error_z) > 100):
                not_control = True
            # print(x_robot, x_robo, z_robot, z)

            pos_robo = (int((x_value/px2mm) + 759 - 40),
                        int((z_value/px2mm) + 341))

            # # ------------------------------------------ robot control start--------------------------------------------------

            x_robo = x_robot
            z = z_robot

            # ----- print current position and TCP angles --------
            ov = client.read('$POS_ACT', debug=True)  # TCP position reading

            # ----------- logic to chose quadrant (TCP angles (A B C)) base on the target z position -------------------
            if z > quad_division_z:
                Q = 1  # variable that indicates the quadrant
                A = -180
                B = 100
                C = -180
            else:
                Q = 2  # variable that indicates the quadrant
                A = -180
                B = 20
                C = -180

            # ------------ logic to check the physical boundries and avoid colision with the cage  ----------------
            if Q == 1:
                if x_robo > q1_x_max:
                    x_robo = q1_x_max
                if x_robo < q1_x_min:
                    x_robo = q1_x_min
                if z > q1_z_max:
                    z = q1_z_max
                if z < q1_z_min:
                    z = q1_z_min

            if Q == 2:
                if x_robo > q2_x_max:
                    x_robo = q2_x_max
                if x_robo < q2_x_min:
                    x_robo = q2_x_min
                if z > q2_z_max:
                    z = q2_z_max
                if z < q2_z_min:
                    z = q2_z_min

            # CONVERSAO PARA MM

            # ----------- logic to send the coordinates to KUKA -------------
            # Defines the vaiable type to E6POS and the movment to PTP

            # print(pos_robo)
            # print(next_pos)

            client.write('COM_ACTION', '3', debug=True)
            client.write("COM_POS", str("{X " + str(x_robo) + ", Y " + str(y_default) + ", Z " + str(
                z) + ", A " + str(A) + ", B " + str(B) + ", C " + str(C) + "}"), debug=False)  # Defines join angles
            client.write('COM_ACTION', '3', debug=True)
            client.write("COM_POS", str("{X " + str(x_robo) + ", Y " + str(y_default) + ", Z " + str(
                z) + ", A " + str(A) + ", B " + str(B) + ", C " + str(C) + "}"), debug=False)  # Defines join angles

            cv2.circle(frame, pos_robo, radius, (255, 255, 0), 3)

        # Desenha o círculo com a previsão corrigida
        cv2.circle(frame, next_pos, radius, (255, 0, 0), 3)

        # #------------- Atualiza o rastro do centro -----------------
        # center_trail_est.append(center)
        # center_trail_rast.append(next_pos)
        # if len(center_trail_est) > max_trail_length:
        #     center_trail_est = center_trail_est[-max_trail_length:]
        #     center_trail_rast = center_trail_rast[-max_trail_length:]

        # #---------------- Desenha o rastro -------------------------
        # for i in range(1, len(center_trail_est)):
        #     cv2.line(frame, center_trail_est[i - 1],
        #              center_trail_est[i], (0, 255, 255), 5)
        #     cv2.line(frame, center_trail_rast[i - 1],
        #              center_trail_rast[i], (0, 0, 255), 5, cv2.LINE_AA)

        last_pos = (new_x, new_y)
        prevCircle = (new_x, new_y)
        prevCirclePrev = (x_filt, y_filt)
        # last_pos = next_pos

        last_time = time.time()
    # time.sleep(0.03)
    # flip_img = cv2.flip(frame, 2)

    frame2 = cv2.flip(frame, 0)
    texto = f"Ux: {u_x}"
    cv2.putText(frame2, texto, posicao, fonte, tamanho_fonte, cor, 2)

    texto2 = f"SEM CONTROLE: {not_control}"
    cv2.putText(frame2, texto2, (50, 150), fonte, tamanho_fonte, cor, 2)

    texto3 = f"Numeros de tiros: {tiros}"
    cv2.putText(frame2, texto3, (50, 200), fonte, tamanho_fonte, cor, 2)

    cv2.imshow("Frame", frame2)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

videoCapture.release()
cv2.destroyAllWindows()
