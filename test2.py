import os
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Хуудасны тохиргоо
st.set_page_config(
    page_title="Runbook Cutover Dashboard", page_icon="🚀", layout="wide"
)

st.title("🚀 Runbook & Cutover Task Dashboard")
st.markdown("---")

EXCEL_FILE = "runbook.xlsx"


def load_data():
  if os.path.exists(EXCEL_FILE):
    try:
      df = pd.read_excel(EXCEL_FILE)
    except Exception as e:
      st.error(
          f"⚠️ Файлыг унших явцад алдаа гарлаа. Excel файл нээлттэй байгаа эсэхийг"
          f" шалгана уу: {e}"
      )
      st.stop()

    # Seq багана байхгүй бол автоматаар үүсгэж дугаарлах
    if "Seq" not in df.columns:
      df.insert(0, "Seq", range(1, len(df) + 1))

    # Seq болон Done-оос бусад багануудыг текст болгох
    for col in df.columns:
      if col not in ["Done", "Seq"]:
        df[col] = df[col].fillna("").astype(str)

    if "Done" not in df.columns:
      df.insert(
          1,
          "Done",
          df["Status"].str.lower().isin(["done", "хийсэн", "хийгдсэн"]),
      )
    else:
      df["Done"] = df["Done"].fillna(False).astype(bool)

    # Seq дугаараар нь эрэмбэлэх
    df["Seq"] = pd.to_numeric(df["Seq"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values(by="Seq", ascending=True).reset_index(drop=True)
    return df
  else:
    st.error(f"⚠️ Файл олдсонгүй: {EXCEL_FILE}")
    st.stop()


def save_data(df):
  try:
    # Хадгалахдаа Seq-ээр нь эрэмбэлээд хадгална
    df = df.sort_values(by="Seq", ascending=True).reset_index(drop=True)
    df.to_excel(EXCEL_FILE, index=False)
  except Exception as e:
    st.error(
        f"⚠️ Файл руу хадгалах үед алдаа гарлаа. Excel файлыг хаасан эсэхээ"
        f" шалгана уу! ({e})"
    )


# Session state
if "main_df" not in st.session_state:
  st.session_state["main_df"] = load_data()

df = st.session_state["main_df"]

# ----------------- ШҮҮЛТҮҮРҮҮД (FILTERS) -----------------
st.sidebar.header("🔍 Шүүлтүүр (Filters)")

status_options = ["Бүгд", "Done", "Pending", "Хоосон"]
selected_status = st.sidebar.selectbox("Төлөвөөр шүүх", status_options)

pic_options = ["Бүгд"]
if "PIC" in df.columns:
  existing_pics = [
      str(x)
      for x in df["PIC"].dropna().unique()
      if str(x).strip() != "" and str(x) != "nan"
  ]
  pic_options.extend(existing_pics)

selected_pic = st.sidebar.selectbox(
    "Хариуцагчаар шүүх", list(dict.fromkeys(pic_options))
)

# Огноогоор шүүх шүүлтүүр
date_columns = [
    col
    for col in df.columns
    if any(
        kw in col.lower() for kw in ["date", "огноо", "time", "цаг", "day"]
    )
]
selected_date = "Бүгд"
if date_columns:
  date_col = date_columns[0]
  date_options = ["Бүгд"] + sorted(
      [
          str(x)
          for x in df[date_col].dropna().unique()
          if str(x).strip() != "" and str(x) != "nan"
      ]
  )
  selected_date = st.sidebar.selectbox(
      f"Огноогоор шүүх ({date_col})", date_options
  )

# Шүүлт хийх логик
filtered_mask = pd.Series(True, index=df.index)

if selected_status == "Done":
  filtered_mask &= df["Status"].str.lower() == "done"
elif selected_status == "Pending":
  filtered_mask &= df["Status"].str.lower() == "pending"
elif selected_status == "Хоосон":
  filtered_mask &= (df["Status"] == "") | (df["Status"].str.lower() == "nan")

if selected_pic != "Бүгд" and "PIC" in df.columns:
  filtered_mask &= df["PIC"].astype(str) == selected_pic

if date_columns and selected_date != "Бүгд":
  filtered_mask &= df[date_columns[0]].astype(str) == selected_date

df_filtered = df[filtered_mask].copy()

# ----------------- ТОУУРХУУД (METRICS) -----------------
total_tasks = len(df)
completed_tasks = len(df[df["Status"].str.lower() == "done"])
pending_tasks = len(df[df["Status"].str.lower() == "pending"])

col1, col2, col3 = st.columns(3)
col1.metric("📌 Нийт ажил", total_tasks)
col2.metric("✅ Хийгдсэн ажлууд (Done)", completed_tasks)
col3.metric("⏳ Хүлээгдэж буй (Pending)", pending_tasks)

st.markdown("---")

# ----------------- ХҮСНЭГТ БОЛОН ФОРМ -----------------
st.subheader("📋 Ажлын явцын жагсаалт")
st.caption(
    "💡 'Seq' дугаараа өөрчилж мөрийн байрыг сольж болно. Өөрчлөлт хийгээд"
    " доорх 'Өөрчлөлтийг хадгалах' товчийг дарна уу."
)

column_config = {
    "Seq": st.column_config.NumberColumn(
        "Seq", help="Дарааллын дугаар", format="%d"
    ),
    "Done": st.column_config.CheckboxColumn("Done", default=False),
    "Status": st.column_config.SelectboxColumn(
        "Төлөв (Status)", options=["Done", "Pending", ""], required=False
    ),
}

# Форм доторх хүснэгтийн өндрийг height=500 болгож томрууллаа
with st.form("runbook_form"):
  editor_data = st.data_editor(
      df_filtered,
      column_config=column_config,
      use_container_width=True,
      height=500,  # <-- Энд хүснэгтийн өндрийг томруулж өгөв (хүсвэл 600 болгож болно)
      num_rows="dynamic",
      key="editor_key",
  )

  submit_button = st.form_submit_button("💾 Өөрчлөлтийг хадгалах")

# Хадгалах товч дарагдсан үед л датаг шинэчилж Excel рүү бичих
if submit_button:
  editor_state = st.session_state.get("editor_key", {})
  has_changes = False

  # 1. Засагдсан мөрүүдийг шинэчлэх
  if editor_state.get("edited_rows"):
    changes = editor_state["edited_rows"]
    for row_rel_idx, col_changes in changes.items():
      actual_idx = df_filtered.index[row_rel_idx]

      for col_name, new_val in col_changes.items():
        if col_name == "Seq":
          st.session_state["main_df"].loc[actual_idx, col_name] = (
              int(new_val) if pd.notna(new_val) else 0
          )
        else:
          st.session_state["main_df"].loc[actual_idx, col_name] = str(new_val)
        has_changes = True

        if col_name == "Done":
          if new_val:
            st.session_state["main_df"].loc[actual_idx, "Status"] = "Done"
          else:
            st.session_state["main_df"].loc[actual_idx, "Status"] = ""
        elif col_name == "Status":
          if str(new_val).lower() == "done":
            st.session_state["main_df"].loc[actual_idx, "Done"] = True
          else:
            st.session_state["main_df"].loc[actual_idx, "Done"] = False

  # 2. Шинээр нэмэгдсэн мөрүүдийг бүртгэх
  if editor_state.get("added_rows"):
    new_rows = pd.DataFrame(editor_state["added_rows"])
    if not new_rows.empty:
      for col in new_rows.columns:
        if col not in ["Seq", "Done"]:
          new_rows[col] = new_rows[col].fillna("").astype(str)
      if "Done" not in new_rows.columns:
        new_rows["Done"] = False
      if "Seq" not in new_rows.columns or new_rows["Seq"].isna().all():
        max_seq = (
            st.session_state["main_df"]["Seq"].max()
            if not st.session_state["main_df"].empty
            else 0
        )
        new_rows["Seq"] = range(max_seq + 1, max_seq + 1 + len(new_rows))
      else:
        new_rows["Seq"] = (
            pd.to_numeric(new_rows["Seq"], errors="coerce").fillna(0).astype(int)
        )

      st.session_state["main_df"] = pd.concat(
          [st.session_state["main_df"], new_rows], ignore_index=True
      )
      has_changes = True

  # 3. Устгагдсан мөрүүдийг хасах
  if editor_state.get("deleted_rows"):
    deleted_indices = [
        df_filtered.index[i] for i in editor_state["deleted_rows"]
    ]
    st.session_state["main_df"] = (
        st.session_state["main_df"].drop(deleted_indices).reset_index(drop=True)
    )
    has_changes = True

  if has_changes:
    # Seq дугаараар нь эрэмбэлж хадгалах
    st.session_state["main_df"] = st.session_state["main_df"].sort_values(
        by="Seq", ascending=True
    ).reset_index(drop=True)
    save_data(st.session_state["main_df"])
    st.success("✅ Амжилттай хадгалагдаж, дараалал шинэчлэгдлээ!")
  else:
    st.info("ℹ️ Өөрчлөлт хийгдээгүй байна.")

st.markdown("---")

# ----------------- ГРАФИКУУД -----------------
g1, g2 = st.columns(2)

with g1:
  st.subheader("📊 Төлөвийн харьцаа")
  if "Status" in df.columns:
    status_counts = df["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    fig_status = px.pie(
        status_counts, names="Status", values="Count", hole=0.4
    )
    st.plotly_chart(fig_status, use_container_width=True)

with g2:
  st.subheader("👤 PIC (Хариуцагч тус бүрээр)")
  if "PIC" in df.columns:
    pic_counts = df["PIC"].value_counts().reset_index()
    pic_counts.columns = ["PIC", "Count"]
    fig_pic = px.bar(
        pic_counts, x="PIC", y="Count", color="PIC", text_auto=True
    )
    st.plotly_chart(fig_pic, use_container_width=True)
