# dashboard_final_mobile.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import requests
from PIL import Image
import io

# Configuración de la página para móviles
st.set_page_config(
    page_title="Dashboard de Producción - Adimatec",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar logo
@st.cache_data
def load_logo(url):
    try:
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content))
        return image
    except:
        return None

logo = load_logo("https://i.postimg.cc/hjfVhfXf/Logo-Adimatec.jpg")

# Título principal con logo
col_logo, col_title, col_icon = st.columns([1, 3, 1])
with col_logo:
    if logo:
        st.image(logo, width=100)
with col_title:
    st.title("Dashboard de Producción - Adimatec")
with col_icon:
    st.markdown(
        """
        <div style='text-align: right; margin-top: 20px;'>
            <span style='font-size: 2em;'>🏭</span>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

@st.cache_data(ttl=3600)  # Cache de 1 hora para actualizaciones automáticas
def load_data():
    """Cargar datos desde Google Sheets"""
    try:
        # REEMPLAZA ESTAS URLs CON LAS DE TUS GOOGLE SHEETS
        # URL para OT_MASTER
        ot_master_url = "https://docs.google.com/spreadsheets/d/17eEYewfzoBZXkFWBm5DOJp3IuvHg9WvN/edit?usp=sharing&ouid=115443194527122417791&rtpof=true&sd=true"
        ot_master_csv = ot_master_url.replace('/edit?usp=sharing', '/export?format=csv')
        
        # URL para PROCESOS  
        procesos_url = "https://docs.google.com/spreadsheets/d/17eEYewfzoBZXkFWBm5DOJp3IuvHg9WvN/edit?usp=sharing&ouid=115443194527122417791&rtpof=true&sd=true"
        procesos_csv = procesos_url.replace('/edit?usp=sharing', '/export?format=csv')
        
        # Cargar datos desde Google Sheets
        ot_master = pd.read_csv(ot_master_csv)
        procesos = pd.read_csv(procesos_csv)
        
        return ot_master, procesos
    except Exception as e:
        st.error(f"Error al cargar los datos desde Google Sheets: {e}")
        st.info("Asegúrate de que las URLs de Google Sheets sean correctas y estén publicadas")
        return None, None

# Cargar datos
ot_master, procesos = load_data()

if ot_master is None or procesos is None:
    st.stop()

# Sidebar con filtros
st.sidebar.header("🔍 Filtros")

# Convertir fechas en ot_master
date_columns = ['fecha_entrega', 'fecha_impresion', 'fecha_terminado', 'fecha_entregada']
for col in date_columns:
    if col in ot_master.columns:
        ot_master[col] = pd.to_datetime(ot_master[col], errors='coerce')

# Convertir fechas en procesos
date_columns_procesos = ['fecha_inicio_1', 'fecha_inicio_2']
for col in date_columns_procesos:
    if col in procesos.columns:
        procesos[col] = pd.to_datetime(procesos[col], errors='coerce')

# Filtros
clientes = ['Todos'] + sorted(ot_master['cliente'].dropna().unique().tolist())
cliente_seleccionado = st.sidebar.selectbox("Cliente", clientes)

estatus_options = ['Todos'] + sorted(ot_master['estatus'].dropna().unique().tolist())
estatus_seleccionado = st.sidebar.selectbox("Estatus", estatus_options)

# Filtro de OT
ots = ["Todas"] + sorted(ot_master['ot'].astype(str).unique().tolist())
ot_seleccionada = st.sidebar.selectbox("OT", ots)

# Filtro de fechas
st.sidebar.subheader("Filtro por Fecha de Entrega")
min_date = ot_master['fecha_entrega'].min()
max_date = ot_master['fecha_entrega'].max()
if pd.notna(min_date) and pd.notna(max_date):
    fecha_inicio = st.sidebar.date_input("Fecha inicio", min_date)
    fecha_fin = st.sidebar.date_input("Fecha fin", max_date)
else:
    st.sidebar.warning("No hay fechas válidas para filtrar")
    fecha_inicio = None
    fecha_fin = None

# Aplicar filtros
ot_master_filtrado = ot_master.copy()
procesos_filtrados = procesos.copy()

if cliente_seleccionado != 'Todos':
    ot_master_filtrado = ot_master_filtrado[ot_master_filtrado['cliente'] == cliente_seleccionado]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'].isin(ot_master_filtrado['ot'])]

if estatus_seleccionado != 'Todos':
    ot_master_filtrado = ot_master_filtrado[ot_master_filtrado['estatus'] == estatus_seleccionado]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'].isin(ot_master_filtrado['ot'])]

if ot_seleccionada != 'Todas':
    ot_master_filtrado = ot_master_filtrado[ot_master_filtrado['ot'] == ot_seleccionada]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'] == ot_seleccionada]

if fecha_inicio and fecha_fin:
    ot_master_filtrado = ot_master_filtrado[
        (ot_master_filtrado['fecha_entrega'] >= pd.Timestamp(fecha_inicio)) &
        (ot_master_filtrado['fecha_entrega'] <= pd.Timestamp(fecha_fin))
    ]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'].isin(ot_master_filtrado['ot'])]

# NUEVO: Definir estados que NO se consideran vencidos (estados finalizados)
estados_no_vencidos = ['FACTURADO', 'OK', 'OK NO ENTREGADO']  # Agrega otros estados finalizados si es necesario

# Calcular OTs vencidas y por vencer - CORREGIDO: Excluir estados finalizados
hoy = datetime.now()
ot_master_filtrado['estado_entrega'] = ot_master_filtrado.apply(
    lambda row: 
        # Si está en estado finalizado, no se considera vencida ni por vencer
        'Completada' if row['estatus'] in estados_no_vencidos else
        'Vencida' if pd.notna(row['fecha_entrega']) and row['fecha_entrega'] < hoy else 
        'Por vencer' if pd.notna(row['fecha_entrega']) and row['fecha_entrega'] >= hoy and row['fecha_entrega'] <= hoy + timedelta(days=7) else 
        'En plazo',
    axis=1
)

# Métricas principales - En móviles se apilarán verticalmente
st.header("📊 Métricas Principales")

# En móviles, streamlit apilará las columnas verticalmente
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_ots = len(ot_master_filtrado)
    st.metric("Total OTs", total_ots)

with col2:
    ots_en_proceso = len(ot_master_filtrado[ot_master_filtrado['estatus'] == 'EN PROCESO'])
    st.metric("OTs en Proceso", ots_en_proceso)

with col3:
    ots_facturadas = len(ot_master_filtrado[ot_master_filtrado['estatus'] == 'FACTURADO'])
    st.metric("OTs Facturadas", ots_facturadas)

# CORREGIDO: Contar solo OTs vencidas que NO estén en estados finalizados
with col4:
    ots_vencidas = len(ot_master_filtrado[
        (ot_master_filtrado['estado_entrega'] == 'Vencida') & 
        (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))
    ])
    st.metric("OTs Vencidas", ots_vencidas, delta=-ots_vencidas, delta_color="inverse")

with col5:
    ots_por_vencer = len(ot_master_filtrado[
        (ot_master_filtrado['estado_entrega'] == 'Por vencer') & 
        (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))
    ])
    st.metric("OTs por Vencer", ots_por_vencer, delta=ots_por_vencer, delta_color="off")

st.markdown("---")

# GRÁFICO PRINCIPAL: OTs VENCIDAS Y POR VENCER - CORREGIDO: Excluir estados finalizados
st.header("📅 Estado de Entregas - OTs Vencidas y Por Vencer")

# Contar OTs por estado de entrega, excluyendo estados finalizados para vencidas/por vencer
estado_entrega_counts = ot_master_filtrado['estado_entrega'].value_counts()

# Para el gráfico principal, mostrar solo vencidas y por vencer de OTs activas
estados_interes = ['Vencida', 'Por vencer']
estado_entrega_counts_filtrado = estado_entrega_counts[estado_entrega_counts.index.isin(estados_interes)]

if not estado_entrega_counts_filtrado.empty:
    fig = px.bar(
        x=estado_entrega_counts_filtrado.index,
        y=estado_entrega_counts_filtrado.values,
        title="OTs Vencidas y Por Vencer (Solo OTs Activas)",
        labels={'x': 'Estado de Entrega', 'y': 'Cantidad de OTs'},
        color=estado_entrega_counts_filtrado.index,
        color_discrete_map={'Vencida': '#FF4B4B', 'Por vencer': '#FFA500'},
        text=estado_entrega_counts_filtrado.values
    )
    
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    fig.update_layout(
        showlegend=False,
        yaxis_title="Cantidad de OTs",
        xaxis_title="",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay OTs vencidas o por vencer con los filtros actuales.")

# Detalle de OTs vencidas y por vencer - CORREGIDO: Excluir estados finalizados
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 OTs Vencidas (Solo Activas)")
    # CORREGIDO: Excluir OTs en estados finalizados
    ots_vencidas_df = ot_master_filtrado[
        (ot_master_filtrado['estado_entrega'] == 'Vencida') & 
        (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))
    ][['ot', 'cliente', 'fecha_entrega', 'estatus']]
    if not ots_vencidas_df.empty:
        st.dataframe(ots_vencidas_df, use_container_width=True, height=200)
        st.caption(f"Total OTs vencidas activas: {len(ots_vencidas_df)}")
    else:
        st.info("No hay OTs vencidas activas")

with col2:
    st.subheader("📋 OTs por Vencer (Próximos 7 días, Solo Activas)")
    # CORREGIDO: Excluir OTs en estados finalizados
    ots_por_vencer_df = ot_master_filtrado[
        (ot_master_filtrado['estado_entrega'] == 'Por vencer') & 
        (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))
    ][['ot', 'cliente', 'fecha_entrega', 'estatus']]
    if not ots_por_vencer_df.empty:
        st.dataframe(ots_por_vencer_df, use_container_width=True, height=200)
        st.caption(f"Total OTs por vencer activas: {len(ots_por_vencer_df)}")
    else:
        st.info("No hay OTs por vencer activas")

# NUEVA SECCIÓN: Mostrar OTs completadas (FACTURADO, OK, etc.) por separado
st.markdown("---")
st.header("✅ OTs Completadas")

# Filtrar OTs completadas
ots_completadas_df = ot_master_filtrado[
    ot_master_filtrado['estatus'].isin(estados_no_vencidos)
][['ot', 'cliente', 'fecha_entrega', 'estatus', 'fecha_terminado']]

if not ots_completadas_df.empty:
    st.dataframe(ots_completadas_df, use_container_width=True, height=200)
    st.caption(f"Total OTs completadas: {len(ots_completadas_df)}")
else:
    st.info("No hay OTs completadas con los filtros actuales")

st.markdown("---")

# [EL RESTO DEL CÓDIGO SE MANTIENE EXACTAMENTE IGUAL - GRÁFICOS EXISTENTES]
# Gráficos existentes - En móviles se apilarán
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 OTs por Cliente")
    if not ot_master_filtrado.empty:
        ots_por_cliente = ot_master_filtrado['cliente'].value_counts()
        fig = px.pie(
            values=ots_por_cliente.values,
            names=ots_por_cliente.index,
            title="Distribución de OTs por Cliente"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos para mostrar")

with col2:
    st.subheader("🎯 OTs por Estatus")
    if not ot_master_filtrado.empty:
        ots_por_estatus = ot_master_filtrado['estatus'].value_counts()
        fig = px.bar(
            x=ots_por_estatus.index,
            y=ots_por_estatus.values,
            title="OTs por Estado",
            labels={'x': 'Estatus', 'y': 'Cantidad'},
            color=ots_por_estatus.index
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos para mostrar")

# Gráfico de procesos
st.subheader("🔧 Procesos más Comunes")
if not procesos_filtrados.empty:
    procesos_count = procesos_filtrados['proceso'].value_counts().head(10)
    fig = px.bar(
        x=procesos_count.values,
        y=procesos_count.index,
        orientation='h',
        title="Top 10 Procesos más Frecuentes",
        labels={'x': 'Frecuencia', 'y': 'proceso'},
        color=procesos_count.values
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos de procesos para mostrar")

# GRÁFICO MEJORADO: Horas Estimadas vs Horas Reales (CON DATOS REALES)
st.subheader("⏰ Horas Estimadas vs Horas Reales por Proceso")

if not procesos_filtrados.empty and 'horas_reales' in procesos_filtrados.columns:
    # Agrupar por proceso y sumar horas estimadas y reales
    horas_por_proceso = procesos_filtrados.groupby('proceso').agg({
        'horas_estimadas': 'sum',
        'horas_reales': 'sum'
    }).reset_index()

    # Tomar los top 10 procesos por horas estimadas
    top_procesos = horas_por_proceso.nlargest(10, 'horas_estimadas')

    # Crear gráfico de barras comparativo
    fig = go.Figure()

    # Barras para horas estimadas
    fig.add_trace(go.Bar(
        name='Horas Estimadas',
        x=top_procesos['proceso'],
        y=top_procesos['horas_estimadas'],
        marker_color='#1f77b4',
        text=top_procesos['horas_estimadas'].round(1),
        textposition='outside'
    ))

    # Barras para horas reales
    fig.add_trace(go.Bar(
        name='Horas Reales',
        x=top_procesos['proceso'],
        y=top_procesos['horas_reales'],
        marker_color='#ff7f0e',
        text=top_procesos['horas_reales'].round(1),
        textposition='outside'
    ))

    fig.update_layout(
        title="Comparación: Horas Estimadas vs Reales por Proceso (Datos Reales)",
        xaxis_title="Proceso",
        yaxis_title="Horas",
        barmode='group',
        height=500,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # Métricas de eficiencia con datos reales
    st.subheader("📊 Eficiencia en Horas (Datos Reales)")
    
    total_horas_estimadas = procesos_filtrados['horas_estimadas'].sum()
    total_horas_reales = procesos_filtrados['horas_reales'].sum()
    
    if total_horas_estimadas > 0:
        eficiencia_global = (total_horas_estimadas / total_horas_reales * 100).round(1)
        diferencia_horas = total_horas_reales - total_horas_estimadas
    else:
        eficiencia_global = 0
        diferencia_horas = 0
    
    # En móviles, estas métricas se apilarán
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Horas Estimadas Totales", f"{total_horas_estimadas:.1f}")
    
    with col2:
        st.metric("Horas Reales Totales", f"{total_horas_reales:.1f}")
    
    with col3:
        st.metric("Diferencia", f"{diferencia_horas:.1f}", 
                 delta=f"{diferencia_horas:.1f}")
    
    with col4:
        st.metric("Eficiencia", f"{eficiencia_global}%")
    
    # Análisis adicional por proceso
    st.subheader("📈 Análisis de Eficiencia por Proceso")
    
    # Calcular eficiencia por proceso
    horas_por_proceso['eficiencia'] = (horas_por_proceso['horas_estimadas'] / horas_por_proceso['horas_reales'] * 100).round(1)
    horas_por_proceso['diferencia'] = horas_por_proceso['horas_reales'] - horas_por_proceso['horas_estimadas']
    
    # Mostrar tabla de eficiencia
    st.dataframe(
        horas_por_proceso[['proceso', 'horas_estimadas', 'horas_reales', 'diferencia', 'eficiencia']]
        .sort_values('eficiencia', ascending=False)
        .round(1),
        use_container_width=True,
        height=300
    )
    
else:
    st.error("No se encontraron datos de horas reales en la migración.")

# Tablas de datos
st.markdown("---")
st.header("📋 Datos Detallados")

tab1, tab2 = st.tabs(["OT Master", "Procesos"])

with tab1:
    st.subheader("Tabla OT Master")
    # Seleccionar columnas relevantes para mostrar
    columnas_mostrar = ['ot', 'descripcion', 'cliente', 'estatus', 'fecha_entrega', 'horas_estimadas_ot', 'horas_reales_ot']
    columnas_disponibles = [col for col in columnas_mostrar if col in ot_master_filtrado.columns]
    
    st.dataframe(
        ot_master_filtrado[columnas_disponibles],
        use_container_width=True,
        hide_index=True
    )
    
    # Opción de descarga
    csv_ot = ot_master_filtrado.to_csv(index=False)
    st.download_button(
        label="📥 Descargar OT Master como CSV",
        data=csv_ot,
        file_name="ot_master_filtrado.csv",
        mime="text/csv"
    )

with tab2:
    st.subheader("Tabla Procesos")
    # Seleccionar columnas relevantes para mostrar
    columnas_mostrar_procesos = ['ot', 'proceso', 'horas_estimadas', 'horas_reales', 'empleado_1', 'empleado_2']
    columnas_disponibles_procesos = [col for col in columnas_mostrar_procesos if col in procesos_filtrados.columns]
    
    st.dataframe(
        procesos_filtrados[columnas_disponibles_procesos],
        use_container_width=True,
        hide_index=True
    )
    
    # Opción de descarga
    csv_procesos = procesos_filtrados.to_csv(index=False)
    st.download_button(
        label="📥 Descargar Procesos como CSV",
        data=csv_procesos,
        file_name="procesos_filtrados.csv",
        mime="text/csv"
    )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Dashboard de Producción - Adimatec | Desarrollado con Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)
