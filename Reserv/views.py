from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from .models import Doctor, Appointment
from app.firebase_config import db
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from firebase_admin import firestore

def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        
        # Verificar las credenciales en Firestore
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).where('password', '==', password).stream()

        user_exists = False
        user_data = None
        for user in query:
            user_exists = True
            user_data = user.to_dict()
            break
        
        if user_exists:
            # Crear el usuario en Django si no existe
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(username=email, email=email, password=password)
            
            # Autenticar al usuario en Django
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                role = user_data.get('role')
                if role == 'doctor':
                    return redirect('home')
                elif role == 'cliente':
                    return redirect('home')
            else:
                messages.error(request, 'Error de autenticación en Django')
        else:
            messages.error(request, 'Credenciales incorrectas')
    
    # Si no es una solicitud POST, renderizar la página de login
    return render(request, 'Reserv/login.html')

from app.firebase_config import db  # Asegúrate de importar la configuración de Firestore

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect('register')

        # Verificar si el usuario ya existe en Django
        if User.objects.filter(email=email).exists():
            messages.error(request, "El correo ya está registrado.")
            return redirect('register')

        try:
            # Registrar al usuario en Django
            user = User.objects.create_user(username=email, email=email, password=password)
            user.save()

            # Agregar el usuario a Firestore
            db.collection('users').add({
                'email': email,
                'password': password,  # Nota: Almacenar contraseñas en texto plano no es seguro
                'role': 'cliente'  # Agregar un rol predeterminado si es necesario
            })

            messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect('login')  # Redirigir a la pantalla de inicio de sesión
        except Exception as e:
            messages.error(request, f"Error al registrar al usuario: {e}")
            return redirect('register')
    
    return render(request, 'Reserv/register.html')  # Renderizar la página de registro



@login_required
def home(request):
    # Obtener la lista de doctores desde Firestore
    doctors_ref = db.collection('Doctors')
    doctors = [doc.to_dict() for doc in doctors_ref.stream()]
    
    return render(request, 'Reserv/home.html', {'Doctors': doctors})

@login_required
def citas_view(request):
    # Obtener las citas del usuario desde Firestore
    appointments_ref = db.collection('Appointments').where('user', '==', request.user.username).stream()
    appointments = [appointment.to_dict() for appointment in appointments_ref]

    # Para cada cita, obtener la información del doctor, incluyendo la imagen
    for cita in appointments:
        doctor_id = cita['doctor_id']
        doctor_ref = db.collection('Doctors').document(str(doctor_id))
        doctor_doc = doctor_ref.get()

        if doctor_doc.exists:
            doctor = doctor_doc.to_dict()
            # Obtener la URL de la imagen del doctor (almacenada en 'picture')
            cita['doctor']['picture'] = doctor.get('picture', 'default_image_url')  # Cambia 'default_image_url' si es necesario
    
    return render(request, 'Reserv/citas.html', {'Appointments': appointments})


def logout_view(request):
    logout(request)
    return redirect('login')

# Lista de control para reservas
reservas = [None] * 5  # Un máximo de 5 reservas

@login_required
def reserve_view(request, id):
    # Buscar el doctor por id en Firestore (colección 'Doctors')
    doctor_ref = db.collection('Doctors').document(str(id))
    doctor = doctor_ref.get().to_dict()

    if doctor is None:
        return redirect('home')  # Si no se encuentra el doctor, redirigir a home

    # Verificar si el doctor ya tiene una reserva
    if not doctor.get('available', True):  # Verificamos si el doctor está disponible
        return render(request, 'Reserv/error.html', {'message': 'Este doctor ya tiene una reserva.'})

    # Si el doctor está disponible y no tiene reserva
    if request.method == 'POST':
        nombre_cliente = request.POST.get('nombre')  # Usar el nombre proporcionado en el formulario
        rut_cliente = request.POST.get('rut')  # Obtener el RUT
        telefono_cliente = request.POST.get('telefono')  # Obtener el teléfono
        email_cliente = request.POST.get('email')  # Obtener el email
        paciente_id = request.user.id  # Usar el id del usuario autenticado

        if nombre_cliente and rut_cliente and telefono_cliente and email_cliente:
            # Crear la reserva en la colección 'Appointments' de Firestore
            db.collection('Appointments').add({
                'doctor_id': str(id),  # ID del doctor
                'name_patient': nombre_cliente,
                'rut_patient': rut_cliente,  # Guardar el RUT del paciente
                'phone_patient': telefono_cliente,  # Guardar el teléfono
                'email_patient': email_cliente,  # Guardar el email
                'client_id': paciente_id,  # ID del usuario
                'status': 'reservado',  # Estatus de la reserva
                'date_created': firestore.SERVER_TIMESTAMP  # Fecha de creación de la reserva
            })

            # Marcar al doctor como no disponible en Firestore
            doctor_ref.update({'available': False})

            # Renderizar la página de éxito mostrando los detalles del doctor y el paciente
            return render(request, 'Reserv/exito.html', {'doctor': doctor, 'nombre_cliente': nombre_cliente})

        else:
            return render(request, 'Reserv/error.html', {'message': 'Por favor ingrese todos los datos necesarios para realizar la reserva.'})

    # Si la solicitud no es POST, renderiza el formulario de reserva
    return render(request, 'Reserv/reserva.html', {'doctor': doctor})


@login_required
def mis_citas(request):
    # Filtrar las citas reservadas por el usuario desde Firestore
    reservations_ref = db.collection('Appointments').where('client_id', '==', request.user.id).stream()
    citas_reservadas = []
    
    for reservation in reservations_ref:
        cita = reservation.to_dict()
        cita['id'] = reservation.id  # Añadir el ID de la cita para poder eliminarla
        # Obtener la información del doctor
        doctor_ref = db.collection('Doctors').document(str(cita['doctor_id']))
        doctor = doctor_ref.get().to_dict()
        cita['doctor'] = doctor
        citas_reservadas.append(cita)

    if not citas_reservadas:
        mensaje = "No tienes citas reservadas."
    else:
        mensaje = None

    return render(request, 'Reserv/mis_citas.html', {'citas': citas_reservadas, 'mensaje': mensaje})


@login_required
def editar_cita(request, cita_id):
    # Get the appointment reference from Firestore
    appointment_ref = db.collection('Appointments').document(cita_id)
    appointment = appointment_ref.get()

    if not appointment.exists:
        messages.error(request, "La cita no existe.")
        return redirect('mis_citas')

    appointment_data = appointment.to_dict()
    
    # Get doctor information
    doctor_ref = db.collection('Doctors').document(str(appointment_data['doctor_id']))
    doctor = doctor_ref.get().to_dict()

    if request.method == 'POST':
        # Get updated data from the form
        nombre_cliente = request.POST.get('nombre')
        rut_cliente = request.POST.get('rut')
        telefono_cliente = request.POST.get('telefono')
        email_cliente = request.POST.get('email')

        if nombre_cliente and rut_cliente and telefono_cliente and email_cliente:
            # Update the appointment in Firestore
            appointment_ref.update({
                'name_patient': nombre_cliente,
                'rut_patient': rut_cliente,
                'phone_patient': telefono_cliente,
                'email_patient': email_cliente,
                'last_modified': firestore.SERVER_TIMESTAMP
            })

            messages.success(request, "Cita actualizada exitosamente.")
            return redirect('mis_citas')
        else:
            messages.error(request, "Por favor complete todos los campos.")

    context = {
        'appointment': appointment_data,
        'doctor': doctor
    }
    return render(request, 'Reserv/editar_cita.html', context)

@login_required
def eliminar_cita(request, cita_id):
    # Obtener la cita desde la colección 'Appointments' usando cita_id
    cita_ref = db.collection('Appointments').document(cita_id)
    cita = cita_ref.get().to_dict()

    if cita is None:
        return redirect('mis_citas')  # Si no se encuentra la cita, redirigir a la página de mis citas
    
    # Obtener el ID del doctor asociado con esta cita
    doctor_id = cita.get('doctor_id')

    if doctor_id:
        # Obtener el doctor desde la colección 'Doctors'
        doctor_ref = db.collection('Doctors').document(doctor_id)
        doctor = doctor_ref.get().to_dict()

        # Eliminar la cita de la colección 'Appointments'
        cita_ref.delete()

        # Verificar si el doctor tiene otras citas, si no tiene, marcarlo como disponible
        citas_restantes = db.collection('Appointments').where('doctor_id', '==', doctor_id).get()
        if not citas_restantes:  # Si no quedan citas para ese doctor
            doctor_ref.update({'available': True})

    return redirect('mis_citas')