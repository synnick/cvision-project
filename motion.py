import cv
import math
import sys

########################################################################################
#Simple funcion usada para calcular la distancia entre dos puntos.
########################################################################################
def distance(p1, p2):
  x1, y1 = p1
  x2, y2 = p2
  return math.sqrt( (y2 - y1)**2 + (x2 - x1)**2)

########################################################################################
#Funcion usada para calcular el cambo de tamano de una imagen.
########################################################################################
def calculate_resize(actual_size, input_size):
  max_actual = max(actual_size)
  max_input = max(input_size)
  rate_change = float(max_input) / max_actual
  return tuple([int(i*rate_change) for i in actual_size])

########################################################################################
#Propiedades de la captura de imagenes desde la camara.
########################################################################################
WIDTH = 620 #Ancho de video a usar
HEIGHT = 440 #Alto de video a usar
#FPS = 30
#BRIGHTNESS = 200
#CONTRAST = 200
DIAGONAL = distance((0, 0), (WIDTH, HEIGHT)) #Distancia Maxima del video
GAUSSIAN_BLUR_FACTOR = 3 #Tamano de la matriz usada para eliminar ruido la primera vez
NFEATURES = 100 #Numero maximo de caracterististicas a buscar
NFRAMES = None #Numero de frames a usar, si se utiliza un archivo
VIDEOFILE = False
PLAY = False
TEXT_FONT = cv.InitFont(cv.CV_FONT_HERSHEY_COMPLEX, .5, .5, 0.0, 1, cv.CV_AA )
########################################################################################
#Inicializacion de lectura de frames. Si se especifico un archivo de video como argumento
#desde la linea de comandos, se utiliza dicho video, si no se utiliza la webcam.
########################################################################################
c = cv.CreateCameraCapture(0) #Usar camara 0 (camara web)
if ".avi" in sys.argv[1]:
  VIDEOFILE = True
  c = cv.CaptureFromFile( sys.argv[1] ) #Usar camara 0 (camara web)
  NFRAMES = cv.GetCaptureProperty( c, cv.CV_CAP_PROP_FRAME_COUNT  )

########################################################################################
#Propiedades de la captura de imagenes desde la webcam.
########################################################################################
cv.SetCaptureProperty( c, cv.CV_CAP_PROP_FRAME_WIDTH, WIDTH ) #Ajustar ancho de video
cv.SetCaptureProperty( c, cv.CV_CAP_PROP_FRAME_HEIGHT, HEIGHT ) #Ajustar altura de video

#cv.SetCaptureProperty( c, cv.CV_CAP_PROP_FPS, FPS )
#cv.SetCaptureProperty( c, cv.CV_CAP_PROP_BRIGHTNESS, BRIGHTNESS ) 
#cv.SetCaptureProperty( c, cv.CV_CAP_PROP_CONTRAST, CONTRAST ) #

########################################################################################
#Inicializacion de variables para diferentes imagenes usadas en los calculos
#de caracteristicas y flujo optico.
########################################################################################
frame = cv.QueryFrame( c ) #Primer frame de la imagen usada para generar copias
ORIGINAL_SIZE = cv.GetSize(frame) #Tamano original del video antes del cambio de tamano
SIZE = (WIDTH, HEIGHT) #Nuevo tamano deseado
#contenedor de la imagen con el nuevo tamano
thumbnail = cv.CreateImage( calculate_resize(ORIGINAL_SIZE, SIZE), frame.depth, frame.nChannels)
#contenedores de parametros para el calculo de las caracteristicas
eig_image = cv.CreateImage(cv.GetSize(thumbnail), cv.IPL_DEPTH_32F, 1)
temp_image = cv.CreateImage(cv.GetSize(thumbnail), cv.IPL_DEPTH_32F, 1)
#contenedor para almacenar las posiciones de las caracteristicas al inicio
frame1_1C = cv.CreateImage( cv.GetSize(thumbnail), cv.IPL_DEPTH_8U, 1 ) 
#contenedor para almacenar las posiciones de las caracteristicas al despues del movimiento
frame2_1C = cv.CreateImage( cv.GetSize(thumbnail), cv.IPL_DEPTH_8U, 1 ) 
#contenedor de parametros usados en el algoritmo Lucas Kanade
pyramid1 = cv.CreateImage( cv.GetSize(thumbnail), cv.IPL_DEPTH_8U, 1 ) 
pyramid2 = cv.CreateImage( cv.GetSize(thumbnail), cv.IPL_DEPTH_8U, 1 ) 
cv.SetCaptureProperty(c, cv.CV_CAP_PROP_POS_FRAMES, 0.0 )
current_frame = 0
########################################################################################
#Loop infinito para ejecutar las rutinas de deteccion de movimiento hasta
#que se presione la tecla esc
########################################################################################
while True:
  if VIDEOFILE: cv.SetCaptureProperty(c, cv.CV_CAP_PROP_POS_FRAMES, current_frame )
  frame = cv.QueryFrame( c ) #primer frame obtenido para el calculo del flujo optico
  if frame == None: break #si no se obtuvo ningun frame, se termino el archivo de video
  cv.Resize(frame, thumbnail) #si se obtuvo un frame, se cambia el tamano al deseado
  output = cv.CloneImage( thumbnail ) #se crea una copia del frame para dibujar sobre el
  #se pasa un filtro gaussiano para reducir ruido
  cv.Smooth( thumbnail, thumbnail, cv.CV_GAUSSIAN, GAUSSIAN_BLUR_FACTOR, GAUSSIAN_BLUR_FACTOR )
  #se voltean las imagenes para corregir un error de opencv
  cv.ConvertImage(thumbnail, frame1_1C, cv.CV_CVTIMG_FLIP)
  #cv.ConvertImage(thumbnail, output, cv.CV_CVTIMG_FLIP)
  frame = cv.QueryFrame( c ) #segundo frame obtenido para el calculo del flujo optico
  if frame == None: break 
  cv.Resize(frame, thumbnail) 
  cv.Smooth( thumbnail, thumbnail, cv.CV_GAUSSIAN, GAUSSIAN_BLUR_FACTOR, GAUSSIAN_BLUR_FACTOR )
  cv.ConvertImage(thumbnail, frame2_1C, cv.CV_CVTIMG_FLIP)

  #obtencion de caracteristicas del primer frame
  frame1_features = cv.GoodFeaturesToTrack(frame1_1C, eig_image, temp_image, NFEATURES, 0.1, 5, None, 3, False)

  #busqueda de caracteristicas del primer frame, en el segundo usando el algoritmo de Lucas Kanade
  frame2_features, status, track_error = cv.CalcOpticalFlowPyrLK(frame1_1C, frame2_1C, pyramid1, pyramid2, frame1_features, 
                            (3, 3), 5,  (cv.CV_TERMCRIT_ITER|cv.CV_TERMCRIT_EPS, 20, 0.03), 0)

  #recorrido de las caracteristicas y dibujo de las flechas
  #utilizando el algoritmo de http://ai.stanford.edu/~dstavens/cs223b/optical_flow_demo.cpp
  for i in range(len(frame2_features)):
    #separamos los puntos iniciales y puntos finales en variables p y q
    p = frame1_features[i]
    q = frame2_features[i]
    p = int(p[0]), int(p[1])
    angle = math.atan2(p[1] - q [1], p[0] - q[0]) #calculamos el angulo entre ellos
    hypotenuse = math.sqrt(math.pow(p[1] - q[1], 2) + math.pow(p[0] - q[0], 2))
    q = (int(p[0] - 3*hypotenuse * math.cos(angle)), int(p[1] - 3*hypotenuse * math.sin(angle)))
    #eliminacion de ruido (movimientos bruscos de un lado de la imagen al otro)
    if distance(p, q) > DIAGONAL * 0.2:
      continue
    #mas eliminacion de ruido (pequenos movimientos casi nulos)
    elif distance(p, q) < 10:
      continue
    p = (p[0], HEIGHT - p[1])
    q = (q[0], HEIGHT - q[1])

    #dibujo de las flechas de flujo optico
    cv.Line( output, p, q, cv.CV_RGB(255, 0, 0), 1, cv.CV_AA, 0 )
    p = (int(q[0] + 9 * math.cos(angle + math.pi / 4)), int(q[1] + 9 * math.sin(angle + math.pi/4)))
    cv.Line( output, p, q, cv.CV_RGB(255, 0, 0), 1, cv.CV_AA, 0 )
    p = (int(q[0] + 9 * math.cos(angle - math.pi / 4)), int(q[1] + 9 * math.sin(angle - math.pi/4)))
    cv.Line( output, p, q, cv.CV_RGB(255, 0, 0), 1, cv.CV_AA, 0 )
  text = ""
  key = cv.WaitKey(7) % 0x100
  if key == 27 or key == 10:
    break
  if VIDEOFILE:
    if chr(key) == 'n' or chr(key) == 'N':
      current_frame += 1.0
    elif chr(key) == 'b' or chr(key) == 'B':
      current_frame -= 1.0
    elif chr(key) == 'p' or chr(key) == 'P':
      PLAY = not PLAY
    
    if (chr(key) == 's' or chr(key) == 'S') and not PLAY:
      cv.SaveImage("output_frame_%s.jpg"%current_frame, output)
      cv.PutText( output, "Frame guardado", (5, 30), TEXT_FONT, cv.CV_RGB(255, 255, 255))

    if PLAY:
      current_frame += 1
      text = "Estado Actual: (Play)"
    else:
      text = "Estado Actual: (Pausa)"

    if current_frame < 0.0: 
      print "Se llego al principio del video, no se puede ir mas atras"
      current_frame = 0.0
    elif current_frame >= NFRAMES - 1: 
      print "Final del video, no se puede ir mas adelante"
      current_frame = NFRAMES - 2

  cv.PutText( output, text, (5, 15), TEXT_FONT, cv.CV_RGB(255, 255, 255) )
  cv.ShowImage("Deteccion de Movimiento", output) #mostrar los resultados en el feed de video 

print "Fin"






