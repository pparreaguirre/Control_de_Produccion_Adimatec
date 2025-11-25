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

# Nuevos imports para PowerPoint
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import tempfile
import zipfile
import os

# Configuración de la página para móviles
st.set_page_config(
    page_title="Dashboard de Producción - Adimatec",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Limpiar cache para desarrollo
st.cache_data.clear()

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

@st.cache_data(ttl=300)  # 5 minutos para testing
def load_data():
    """Cargar datos desde Google Sheets"""
    try:
        # Sheet ID (la parte larga después de /d/)
        sheet_id = "17eEYewfzoBZXkFWBm5DOJp3IuvHg9WvN"
        
        # URLs CORREGIDAS - formato de exportación directa
        ot_master_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=525532145"
        procesos_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=240160734"
        
        # Cargar datos
        ot_master = pd.read_csv(ot_master_csv)
        procesos = pd.read_csv(procesos_csv)
        
        return ot_master, procesos
    except Exception as e:
        st.error(f"Error al cargar los datos desde Google Sheets: {e}")
        return None, None

# Cargar datos
ot_master, procesos = load_data()

if ot_master is None or procesos is None:
    st.stop()

# Asegurar que la columna 'ot' sea string en ambos dataframes
ot_master['ot'] = ot_master['ot'].astype(str)
procesos['ot'] = procesos['ot'].astype(str)

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

# Filtros principales
clientes = ['Todos'] + sorted(ot_master['cliente'].dropna().unique().tolist())
cliente_seleccionado = st.sidebar.selectbox("Cliente", clientes)

estatus_options = ['Todos'] + sorted(ot_master['estatus'].dropna().unique().tolist())
estatus_seleccionado = st.sidebar.selectbox("Estatus", estatus_options)

# Filtro de OT
ots = ["Todas"] + sorted(ot_master['ot'].astype(str).unique().tolist())
ot_seleccionada = st.sidebar.selectbox("OT", ots)

# Filtros de empleados SIN REPETIDOS
st.sidebar.subheader("👥 Filtros por Empleados")

def limpiar_nombre(nombre):
    if pd.isna(nombre) or nombre == '' or nombre == ' ':
        return None
    nombre_limpio = str(nombre)
    nombre_limpio = nombre_limpio.strip()
    nombre_limpio = ' '.join(nombre_limpio.split())
    caracteres_problematicos = ['\n', '\t', '\r', '*', '#', '  ']
    for char in caracteres_problematicos:
        nombre_limpio = nombre_limpio.replace(char, ' ')
    nombre_limpio = nombre_limpio.title()
    nombre_limpio = ' '.join(nombre_limpio.split())
    return nombre_limpio if nombre_limpio != '' else None

# Obtener lista única de empleados
empleados_1 = [limpiar_nombre(x) for x in procesos['empleado_1'].dropna().unique()]
empleados_2 = [limpiar_nombre(x) for x in procesos['empleado_2'].dropna().unique()]
todos_empleados = list(set([emp for emp in empleados_1 + empleados_2 if emp is not None]))
todos_empleados = ['Todos'] + sorted(todos_empleados)

empleado_seleccionado = st.sidebar.selectbox("Empleado", todos_empleados)

# Filtro de fechas
st.sidebar.subheader("📅 Filtro por Fecha de Entrega")
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

if empleado_seleccionado != 'Todos':
    procesos_temp = procesos_filtrados.copy()
    procesos_temp['empleado_1_clean'] = procesos_temp['empleado_1'].apply(limpiar_nombre)
    procesos_temp['empleado_2_clean'] = procesos_temp['empleado_2'].apply(limpiar_nombre)
    procesos_filtrados = procesos_temp[
        (procesos_temp['empleado_1_clean'] == empleado_seleccionado) | 
        (procesos_temp['empleado_2_clean'] == empleado_seleccionado)
    ]
    procesos_filtrados = procesos_filtrados.drop(['empleado_1_clean', 'empleado_2_clean'], axis=1)
    ot_master_filtrado = ot_master_filtrado[ot_master_filtrado['ot'].isin(procesos_filtrados['ot'])]

if fecha_inicio and fecha_fin:
    ot_master_filtrado = ot_master_filtrado[
        (ot_master_filtrado['fecha_entrega'] >= pd.Timestamp(fecha_inicio)) &
        (ot_master_filtrado['fecha_entrega'] <= pd.Timestamp(fecha_fin))
    ]
    procesos_filtrados = procesos_filtrados[procesos_filtrados['ot'].isin(ot_master_filtrado['ot'])]

# Definir estados que NO se consideran vencidos
estados_no_vencidos = ['FACTURADO', 'OK', 'OK NO ENTREGADO']

# Calcular OTs vencidas y por vencer
hoy = datetime.now()
ot_master_filtrado['estado_entrega'] = ot_master_filtrado.apply(
    lambda row: 
        'Completada' if row['estatus'] in estados_no_vencidos else
        'Vencida' if pd.notna(row['fecha_entrega']) and row['fecha_entrega'] < hoy else 
        'Por vencer' if pd.notna(row['fecha_entrega']) and row['fecha_entrega'] >= hoy and row['fecha_entrega'] <= hoy + timedelta(days=7) else 
        'En plazo',
    axis=1
)

# Calcular porcentaje de facturación
total_ots = len(ot_master_filtrado)
ots_facturadas = len(ot_master_filtrado[ot_master_filtrado['estatus'] == 'FACTURADO'])
porcentaje_facturado = (ots_facturadas / total_ots * 100) if total_ots > 0 else 0

# Identificar reprocesos (Garantías)
if 'orden_compra' in ot_master_filtrado.columns:
    ot_master_filtrado['es_reproceso'] = ot_master_filtrado['orden_compra'].str.contains('GARANTIA', case=False, na=False)
    total_reprocesos = ot_master_filtrado['es_reproceso'].sum()
    porcentaje_reprocesos = (total_reprocesos / total_ots * 100) if total_ots > 0 else 0
else:
    total_reprocesos = 0
    porcentaje_reprocesos = 0

# Calcular desviaciones de horas
if 'horas_estimadas_ot' in ot_master_filtrado.columns and 'horas_reales_ot' in ot_master_filtrado.columns:
    ot_con_horas = ot_master_filtrado[
        (ot_master_filtrado['horas_estimadas_ot'].notna()) & 
        (ot_master_filtrado['horas_reales_ot'].notna())
    ].copy()
    ot_con_horas['diferencia_horas'] = ot_con_horas['horas_reales_ot'] - ot_con_horas['horas_estimadas_ot']
    ot_con_horas['tipo_desviacion'] = ot_con_horas['diferencia_horas'].apply(
        lambda x: 'Desviación Positiva' if x <= 0 else 'Desviación Negativa'
    )
    total_horas_programadas = ot_con_horas['horas_estimadas_ot'].sum()
    horas_desviacion_positiva = ot_con_horas[ot_con_horas['tipo_desviacion'] == 'Desviación Positiva']['horas_reales_ot'].sum()
    horas_desviacion_negativa = ot_con_horas[ot_con_horas['tipo_desviacion'] == 'Desviación Negativa']['horas_reales_ot'].sum()
    porcentaje_positivo = (horas_desviacion_positiva / total_horas_programadas * 100) if total_horas_programadas > 0 else 0
    porcentaje_negativo = (horas_desviacion_negativa / total_horas_programadas * 100) if total_horas_programadas > 0 else 0
else:
    total_horas_programadas = 0
    horas_desviacion_positiva = 0
    horas_desviacion_negativa = 0
    porcentaje_positivo = 0
    porcentaje_negativo = 0

# Métricas principales
st.header("📊 Métricas Principales")
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1: st.metric("Total OTs", total_ots)
with col2: 
    ots_en_proceso = len(ot_master_filtrado[ot_master_filtrado['estatus'] == 'EN PROCESO'])
    st.metric("OTs en Proceso", ots_en_proceso)
with col3: st.metric("OTs Facturadas", ots_facturadas)
with col4: 
    ots_vencidas = len(ot_master_filtrado[(ot_master_filtrado['estado_entrega'] == 'Vencida') & (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))])
    st.metric("OTs Vencidas", ots_vencidas, delta=-ots_vencidas, delta_color="inverse")
with col5: 
    ots_por_vencer = len(ot_master_filtrado[(ot_master_filtrado['estado_entrega'] == 'Por vencer') & (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))])
    st.metric("OTs por Vencer", ots_por_vencer, delta=ots_por_vencer, delta_color="off")
with col6: st.metric("% Facturación", f"{porcentaje_facturado:.1f}%")

st.markdown("---")

# GRÁFICO PRINCIPAL: OTs VENCIDAS Y POR VENCER
st.header("📅 Estado de Entregas - OTs Vencidas y Por Vencer")
estado_entrega_counts = ot_master_filtrado['estado_entrega'].value_counts()
estados_interes = ['Vencida', 'Por vencer']
estado_entrega_counts_filtrado = estado_entrega_counts[estado_entrega_counts.index.isin(estados_interes)]

fig_ots_vencidas = None
if not estado_entrega_counts_filtrado.empty:
    fig_ots_vencidas = px.bar(
        x=estado_entrega_counts_filtrado.index,
        y=estado_entrega_counts_filtrado.values,
        title="OTs Vencidas y Por Vencer (Solo OTs Activas)",
        labels={'x': 'Estado de Entrega', 'y': 'Cantidad de OTs'},
        color=estado_entrega_counts_filtrado.index,
        color_discrete_map={'Vencida': '#FF4B4B', 'Por vencer': '#FFA500'},
        text=estado_entrega_counts_filtrado.values
    )
    fig_ots_vencidas.update_traces(texttemplate='%{text}', textposition='outside')
    fig_ots_vencidas.update_layout(showlegend=False, yaxis_title="Cantidad de OTs", xaxis_title="", height=400)
    st.plotly_chart(fig_ots_vencidas, use_container_width=True)
else:
    st.info("No hay OTs vencidas o por vencer con los filtros actuales.")

# Detalle de OTs vencidas y por vencer
col1, col2 = st.columns(2)
with col1:
    st.subheader("📋 OTs Vencidas (Solo Activas)")
    ots_vencidas_df = ot_master_filtrado[(ot_master_filtrado['estado_entrega'] == 'Vencida') & (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))][['ot', 'cliente', 'fecha_entrega', 'estatus']]
    if not ots_vencidas_df.empty: st.dataframe(ots_vencidas_df, use_container_width=True, height=200)
    else: st.info("No hay OTs vencidas activas")
with col2:
    st.subheader("📋 OTs por Vencer (Próximos 7 días, Solo Activas)")
    ots_por_vencer_df = ot_master_filtrado[(ot_master_filtrado['estado_entrega'] == 'Por vencer') & (~ot_master_filtrado['estatus'].isin(estados_no_vencidos))][['ot', 'cliente', 'fecha_entrega', 'estatus']]
    if not ots_por_vencer_df.empty: st.dataframe(ots_por_vencer_df, use_container_width=True, height=200)
    else: st.info("No hay OTs por vencer activas")

# OTs Completadas
st.markdown("---")
st.header("✅ OTs Completadas")
ots_completadas_df = ot_master_filtrado[ot_master_filtrado['estatus'].isin(estados_no_vencidos)][['ot', 'cliente', 'fecha_entrega', 'estatus', 'fecha_terminado']]
if not ots_completadas_df.empty: st.dataframe(ots_completadas_df, use_container_width=True, height=200)
else: st.info("No hay OTs completadas con los filtros actuales")

# REPROCESOS después de OTs Completadas
st.markdown("---")
st.header("🔄 Análisis de Reprocesos")
col1, col2 = st.columns(2)

fig_reprocesos = None
with col1:
    if total_ots > 0 and total_reprocesos > 0:
        fig_reprocesos = px.pie(
            values=[total_reprocesos, total_ots - total_reprocesos],
            names=['Reprocesos', 'OTs Normales'],
            title="Distribución: OTs Normales vs Reprocesos",
            hole=0.4,
            color=['Reprocesos', 'OTs Normales'],
            color_discrete_map={'Reprocesos': '#FFA15A', 'OTs Normales': '#636EFA'}
        )
        fig_reprocesos.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_reprocesos, use_container_width=True)
    else: st.info("No hay reprocesos para mostrar")
with col2:
    st.metric("Total Reprocesos", total_reprocesos)
    st.metric("OTs Normales", total_ots - total_reprocesos)
    st.metric("% Reprocesos", f"{porcentaje_reprocesos:.1f}%")
    if total_reprocesos > 0: st.warning(f"Reprocesos identificados: {total_reprocesos} ({porcentaje_reprocesos:.1f}%)")
    else: st.success("✅ No se han identificado reprocesos")

# Gráficos existentes
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.subheader("📈 OTs por Cliente")
    if not ot_master_filtrado.empty and 'cliente' in ot_master_filtrado.columns:
        ots_por_cliente = ot_master_filtrado['cliente'].value_counts()
        if not ots_por_cliente.empty:
            fig_clientes = px.pie(values=ots_por_cliente.values, names=ots_por_cliente.index, title="Distribución de OTs por Cliente")
            st.plotly_chart(fig_clientes, use_container_width=True)
        else: st.info("No hay datos de clientes para mostrar")
    else: st.info("No hay datos para mostrar")
with col2:
    st.subheader("🎯 OTs por Estatus")
    if not ot_master_filtrado.empty and 'estatus' in ot_master_filtrado.columns:
        ots_por_estatus = ot_master_filtrado['estatus'].value_counts()
        if not ots_por_estatus.empty:
            fig_estatus = px.bar(x=ots_por_estatus.index, y=ots_por_estatus.values, title="OTs por Estado", labels={'x': 'Estatus', 'y': 'Cantidad'}, color=ots_por_estatus.index)
            st.plotly_chart(fig_estatus, use_container_width=True)
        else: st.info("No hay datos de estatus para mostrar")
    else: st.info("No hay datos para mostrar")

# NUEVO: GRÁFICO DE DESVIACIONES DE HORAS
st.markdown("---")
st.header("📊 Desviaciones de Horas Programadas")

fig_desviaciones = None
if total_horas_programadas > 0:
    categorias = ['Horas Programadas', 'Desviaciones Positivas', 'Desviaciones Negativas']
    valores = [total_horas_programadas, horas_desviacion_positiva, horas_desviacion_negativa]
    colores = ['#1f77b4', '#2ca02c', '#d62728']
    
    fig_desviaciones = go.Figure()
    fig_desviaciones.add_trace(go.Bar(x=categorias, y=valores, marker_color=colores, text=[f'{val:.1f}h' for val in valores], textposition='outside'))
    fig_desviaciones.update_layout(title="Comparación de Horas Programadas vs Desviaciones", yaxis_title="Horas", xaxis_title="", showlegend=False, height=500)
    st.plotly_chart(fig_desviaciones, use_container_width=True)
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Total Horas Programadas", f"{total_horas_programadas:.1f}h")
    with col2: st.metric("Desviaciones Positivas", f"{horas_desviacion_positiva:.1f}h", f"{porcentaje_positivo:.1f}%")
    with col3: st.metric("Desviaciones Negativas", f"{horas_desviacion_negativa:.1f}h", f"{porcentaje_negativo:.1f}%", delta_color="inverse")
else: st.warning("No hay datos suficientes de horas para mostrar las desviaciones")

# GRÁFICO DE FACTURACIÓN al final
st.markdown("---")
st.header("💰 Porcentaje de Facturación")
col1, col2 = st.columns(2)

fig_facturacion = None
with col1:
    if total_ots > 0:
        fig_facturacion = px.pie(
            values=[ots_facturadas, total_ots - ots_facturadas],
            names=['Facturado', 'No Facturado'],
            title="Total de OTs vs Facturado",
            hole=0.4,
            color=['Facturado', 'No Facturado'],
            color_discrete_map={'Facturado': '#00CC96', 'No Facturado': '#EF553B'}
        )
        fig_facturacion.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_facturacion, use_container_width=True)
    else: st.info("No hay OTs para mostrar el gráfico de facturación")
with col2:
    st.metric("OTs Facturadas", ots_facturadas)
    st.metric("OTs Pendientes", total_ots - ots_facturadas)
    st.metric("Porcentaje de Facturación", f"{porcentaje_facturado:.1f}%")
    if total_ots > 0: st.info(f"Eficiencia de facturación: {porcentaje_facturado:.1f}%")
    else: st.info("No hay OTs para mostrar el resumen de facturación")

# NUEVA SECCIÓN: GENERACIÓN DE POWERPOINT
st.markdown("---")
st.header("📊 Generar Reporte Ejecutivo")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 Presentación PowerPoint")
    st.info("Genera un reporte ejecutivo completo en formato PowerPoint listo para presentar.")
    
    if st.button("🚀 Generar Reporte PowerPoint Completo", type="primary", use_container_width=True):
        generar_powerpoint_completo()

with col2:
    st.subheader("📸 Exportar Gráficos")
    st.info("Descarga todos los gráficos como imágenes PNG para usar en otros reportes.")
    
    if st.button("🖼️ Exportar Gráficos como Imágenes", use_container_width=True):
        exportar_graficos_imagenes()

# FUNCIONES PARA POWERPOINT
def generar_powerpoint_completo():
    """Generar una presentación PowerPoint profesional con todos los gráficos y métricas"""
    try:
        with st.spinner("🔄 Generando reporte ejecutivo en PowerPoint..."):
            # Crear una nueva presentación
            prs = Presentation()
            
            # Slide 1: Portada
            slide = prs.slides.add_slide(prs.slide_layouts[0])
            title = slide.shapes.title
            subtitle = slide.placeholders[1]
            
            title.text = "REPORTE DE PRODUCCIÓN"
            title.text_frame.paragraphs[0].font.size = Pt(44)
            title.text_frame.paragraphs[0].font.bold = True
            
            subtitle.text = f"Adimatec S.A.\n{datetime.now().strftime('%d de %B de %Y')}\nDashboard de Producción"
            subtitle.text_frame.paragraphs[0].font.size = Pt(24)
            
            # Slide 2: Resumen Ejecutivo
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            title = slide.shapes.title
            content = slide.placeholders[1]
            
            title.text = "Resumen Ejecutivo"
            tf = content.text_frame
            tf.text = f"Período: {fecha_inicio if fecha_inicio else 'Inicio'} - {fecha_fin if fecha_fin else 'Actual'}"
            
            p = tf.add_paragraph()
            p.text = f"• Total de OTs Analizadas: {total_ots}"
            p = tf.add_paragraph()
            p.text = f"• OTs Facturadas: {ots_facturadas} ({porcentaje_facturado:.1f}%)"
            p = tf.add_paragraph()
            p.text = f"• OTs en Proceso: {ots_en_proceso}"
            p = tf.add_paragraph()
            p.text = f"• OTs Vencidas: {ots_vencidas}"
            p = tf.add_paragraph()
            p.text = f"• OTs por Vencer: {ots_por_vencer}"
            p = tf.add_paragraph()
            p.text = f"• Reprocesos Identificados: {total_reprocesos} ({porcentaje_reprocesos:.1f}%)"
            
            # Slide 3: Métricas de Performance
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            title = slide.shapes.title
            content = slide.placeholders[1]
            
            title.text = "Métricas Clave de Performance"
            tf = content.text_frame
            tf.text = "Indicadores de Eficiencia Operativa:"
            
            p = tf.add_paragraph()
            p.text = f"📊 Eficiencia en Facturación: {porcentaje_facturado:.1f}%"
            p = tf.add_paragraph()
            p.text = f"⚡ Tasa de Cumplimiento: {((total_ots - ots_vencidas) / total_ots * 100) if total_ots > 0 else 0:.1f}%"
            p = tf.add_paragraph()
            p.text = f"⚠️  Tasa de Reprocesos: {porcentaje_reprocesos:.1f}%"
            p = tf.add_paragraph()
            p.text = f"📅 OTs por Vencer (Próximos 7 días): {ots_por_vencer}"
            p = tf.add_paragraph()
            p.text = f"🔴 OTs Vencidas Críticas: {ots_vencidas}"
            
            # Slide 4: OTs Vencidas y Por Vencer
            if fig_ots_vencidas is not None:
                slide = prs.slides.add_slide(prs.slide_layouts[5])
                title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
                title_frame = title_shape.text_frame
                title_frame.text = "ANÁLISIS DE OTs VENCIDAS Y POR VENCER"
                title_frame.paragraphs[0].font.size = Pt(24)
                title_frame.paragraphs[0].font.bold = True
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile:
                    fig_ots_vencidas.write_image(tmpfile.name, width=1000, height=600, scale=2)
                    slide.shapes.add_picture(tmpfile.name, Inches(0.5), Inches(1.2), width=Inches(9))
                    os.unlink(tmpfile.name)
                
                # Agregar nota explicativa
                nota_shape = slide.shapes.add_textbox(Inches(0.5), Inches(6), Inches(9), Inches(0.8))
                nota_frame = nota_shape.text_frame
                nota_frame.text = f"• OTs Vencidas: {ots_vencidas} | OTs por Vencer: {ots_por_vencer}"
                nota_frame.paragraphs[0].font.size = Pt(14)
                nota_frame.paragraphs[0].font.color.rgb = RGBColor(128, 128, 128)
            
            # Slide 5: Facturación
            if fig_facturacion is not None:
                slide = prs.slides.add_slide(prs.slide_layouts[5])
                title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
                title_frame = title_shape.text_frame
                title_frame.text = "ANÁLISIS DE FACTURACIÓN"
                title_frame.paragraphs[0].font.size = Pt(24)
                title_frame.paragraphs[0].font.bold = True
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile:
                    fig_facturacion.write_image(tmpfile.name, width=800, height=600, scale=2)
                    slide.shapes.add_picture(tmpfile.name, Inches(1), Inches(1.2), width=Inches(8))
                    os.unlink(tmpfile.name)
                
                # Métricas de facturación
                metrics_shape = slide.shapes.add_textbox(Inches(0.5), Inches(6), Inches(9), Inches(1))
                metrics_frame = metrics_shape.text_frame
                metrics_frame.text = f"Eficiencia: {porcentaje_facturado:.1f}% | Pendientes: {total_ots - ots_facturadas} OTs"
                metrics_frame.paragraphs[0].font.size = Pt(16)
            
            # Slide 6: Reprocesos
            if fig_reprocesos is not None and total_reprocesos > 0:
                slide = prs.slides.add_slide(prs.slide_layouts[5])
                title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
                title_frame = title_shape.text_frame
                title_frame.text = "ANÁLISIS DE REPROCESOS"
                title_frame.paragraphs[0].font.size = Pt(24)
                title_frame.paragraphs[0].font.bold = True
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile:
                    fig_reprocesos.write_image(tmpfile.name, width=800, height=600, scale=2)
                    slide.shapes.add_picture(tmpfile.name, Inches(1), Inches(1.2), width=Inches(8))
                    os.unlink(tmpfile.name)
                
                # Análisis de reprocesos
                analysis_shape = slide.shapes.add_textbox(Inches(0.5), Inches(6), Inches(9), Inches(1))
                analysis_frame = analysis_shape.text_frame
                analysis_frame.text = f"Tasa de reprocesos: {porcentaje_reprocesos:.1f}% | {total_reprocesos} OTs identificadas"
                analysis_frame.paragraphs[0].font.size = Pt(16)
            
            # Slide 7: Desviaciones de Horas
            if fig_desviaciones is not None and total_horas_programadas > 0:
                slide = prs.slides.add_slide(prs.slide_layouts[5])
                title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
                title_frame = title_shape.text_frame
                title_frame.text = "DESVIACIONES DE HORAS PROGRAMADAS"
                title_frame.paragraphs[0].font.size = Pt(24)
                title_frame.paragraphs[0].font.bold = True
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile:
                    fig_desviaciones.write_image(tmpfile.name, width=1000, height=600, scale=2)
                    slide.shapes.add_picture(tmpfile.name, Inches(0.5), Inches(1.2), width=Inches(9))
                    os.unlink(tmpfile.name)
                
                # Resumen de desviaciones
                summary_shape = slide.shapes.add_textbox(Inches(0.5), Inches(6), Inches(9), Inches(1))
                summary_frame = summary_shape.text_frame
                summary_frame.text = f"Desviaciones Positivas: {porcentaje_positivo:.1f}% | Negativas: {porcentaje_negativo:.1f}%"
                summary_frame.paragraphs[0].font.size = Pt(16)
            
            # Slide 8: Recomendaciones y Acciones
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            title = slide.shapes.title
            content = slide.placeholders[1]
            
            title.text = "Recomendaciones y Plan de Acción"
            tf = content.text_frame
            tf.text = "Acciones Prioritarias Identificadas:"
            
            if ots_vencidas > 0:
                p = tf.add_paragraph()
                p.text = f"🚨 Atender {ots_vencidas} OTs vencidas críticas"
            if ots_por_vencer > 0:
                p = tf.add_paragraph()
                p.text = f"📅 Revisar {ots_por_vencer} OTs por vencer en próximos 7 días"
            if porcentaje_reprocesos > 5:
                p = tf.add_paragraph()
                p.text = f"🔧 Analizar causas de reprocesos ({porcentaje_reprocesos:.1f}%)"
            if porcentaje_facturado < 80:
                p = tf.add_paragraph()
                p.text = f"💵 Mejorar proceso de facturación ({porcentaje_facturado:.1f}%)"
            
            p = tf.add_paragraph()
            p.text = f"\nPróxima revisión: {(datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y')}"
            
            # Guardar presentación
            filename = f"Reporte_Produccion_Adimatec_{datetime.now().strftime('%Y%m%d_%H%M')}.pptx"
            prs.save(filename)
            
            # Ofrecer descarga
            with open(filename, 'rb') as f:
                st.download_button(
                    label="📥 Descargar Reporte PowerPoint",
                    data=f.read(),
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
            
            st.success("🎉 ¡Reporte ejecutivo generado exitosamente!")
            st.info("💡 **El reporte incluye:** Portada, Resumen Ejecutivo, Métricas Clave, Análisis de OTs Vencidas, Facturación, Reprocesos, Desviaciones de Horas y Plan de Acción.")
            
    except ImportError:
        st.error("""
        **Error:** Se requiere la librería `python-pptx`
        
        Para instalar ejecuta: 
        ```bash
        pip install python-pptx
        ```
        """)
    except Exception as e:
        st.error(f"❌ Error al generar la presentación: {str(e)}")

def exportar_graficos_imagenes():
    """Exportar gráficos individuales como imágenes PNG"""
    try:
        with st.spinner("📸 Exportando gráficos como imágenes..."):
            temp_files = []
            
            # Lista de gráficos a exportar
            graficos = {
                "01_OTs_Vencidas_Por_Vencer.png": fig_ots_vencidas,
                "02_Facturacion.png": fig_facturacion,
                "03_Reprocesos.png": fig_reprocesos,
                "04_Desviaciones_Horas.png": fig_desviaciones,
                "05_OTs_por_Cliente.png": fig_clientes if 'fig_clientes' in locals() else None,
                "06_OTs_por_Estatus.png": fig_estatus if 'fig_estatus' in locals() else None
            }
            
            for filename, figura in graficos.items():
                if figura is not None:
                    try:
                        temp_path = f"temp_{filename}"
                        figura.write_image(temp_path, width=1200, height=800, scale=2)
                        temp_files.append(temp_path)
                    except Exception as e:
                        st.warning(f"No se pudo exportar {filename}: {str(e)}")
            
            if temp_files:
                # Crear ZIP
                zip_filename = f"Graficos_Produccion_Adimatec_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
                with zipfile.ZipFile(zip_filename, 'w') as zipf:
                    for file in temp_files:
                        zipf.write(file, os.path.basename(file))
                
                # Ofrecer descarga
                with open(zip_filename, 'rb') as f:
                    st.download_button(
                        label="📦 Descargar Todos los Gráficos (ZIP)",
                        data=f.read(),
                        file_name=zip_filename,
                        mime="application/zip",
                        use_container_width=True
                    )
                
                # Limpiar archivos temporales
                for file in temp_files + [zip_filename]:
                    if os.path.exists(file):
                        os.remove(file)
                
                st.success(f"✅ {len(temp_files)} gráficos exportados exitosamente!")
                st.info("📁 Los gráficos se descargarán en alta resolución (PNG) comprimidos en un archivo ZIP.")
            else:
                st.warning("⚠️ No hay gráficos disponibles para exportar.")
                
    except Exception as e:
        st.error(f"❌ Error al exportar gráficos: {str(e)}")

# Tablas de datos (se mantienen igual)
st.markdown("---")
st.header("📋 Datos Detallados")
tab1, tab2 = st.tabs(["OT Master", "Procesos"])
with tab1:
    st.subheader("Tabla OT Master")
    columnas_mostrar = ['ot', 'descripcion', 'cliente', 'estatus', 'fecha_entrega', 'horas_estimadas_ot', 'horas_reales_ot']
    columnas_disponibles = [col for col in columnas_mostrar if col in ot_master_filtrado.columns]
    if not ot_master_filtrado.empty:
        st.dataframe(ot_master_filtrado[columnas_disponibles], use_container_width=True, hide_index=True)
        csv_ot = ot_master_filtrado.to_csv(index=False)
        st.download_button(label="📥 Descargar OT Master como CSV", data=csv_ot, file_name="ot_master_filtrado.csv", mime="text/csv")
    else: st.info("No hay datos para mostrar en OT Master")
with tab2:
    st.subheader("Tabla Procesos")
    posibles_nombres = ['proceso', 'Proceso', 'PROCESO', 'proceso_nombre', 'Proceso_Nombre']
    columna_proceso = None
    for nombre in posibles_nombres:
        if nombre in procesos_filtrados.columns:
            columna_proceso = nombre
            break
    columnas_mostrar_procesos = ['ot', columna_proceso, 'horas_estimadas', 'horas_reales', 'empleado_1', 'empleado_2']
    columnas_disponibles_procesos = [col for col in columnas_mostrar_procesos if col in procesos_filtrados.columns]
    if not procesos_filtrados.empty:
        st.dataframe(procesos_filtrados[columnas_disponibles_procesos], use_container_width=True, hide_index=True)
        csv_procesos = procesos_filtrados.to_csv(index=False)
        st.download_button(label="📥 Descargar Procesos como CSV", data=csv_procesos, file_name="procesos_filtrados.csv", mime="text/csv")
    else: st.info("No hay datos para mostrar en Procesos")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Dashboard de Producción - Adimatec | Desarrollado con Streamlit</p>
        <p><small>✨ Incluye generación automática de reportes PowerPoint</small></p>
    </div>
    """,
    unsafe_allow_html=True
)
