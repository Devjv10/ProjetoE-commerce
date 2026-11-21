"""Pequenos componentes compartilhados entre as páginas Streamlit."""
from pathlib import Path
import streamlit as st
from services import cart
from services.products import money

ROOT = Path(__file__).resolve().parents[1]


def token():
    value = st.session_state.get('token')
    cart.authenticate(value)
    return value


def error_message(error):
    if isinstance(error, ValueError):
        st.warning(str(error))
    else:
        st.error(f'Não foi possível concluir a operação ({type(error).__name__}). Verifique as conexões na barra lateral e tente novamente.')


def product_card(product, key_prefix='catalog'):
    with st.container(border=True):
        st.image(str(ROOT / product['imagem']), width='stretch')
        st.caption(f"{product['marca']} · {product['categoria']}")
        st.subheader(product['nome'])
        st.markdown(f"### {money(product['preco_centavos'])}")
        with st.expander('Ver detalhes'):
            st.write(product['descricao'])
            for name, value in product['especificacoes'].items():
                st.write(f'**{name}:** {value}')
        if st.button('Adicionar ao carrinho', key=f"{key_prefix}_{product['_id']}", use_container_width=True):
            try:
                cart.change_cart(token(), product['_id'], 1, add=True)
                st.success('Produto adicionado ao carrinho.')
            except Exception as error:
                error_message(error)


def summary(lines):
    st.dataframe([{'Produto': x['nome'], 'Quantidade': x['quantidade'],
                   'Preço unitário': money(x['preco_centavos']), 'Subtotal': money(x['subtotal_centavos'])}
                  for x in lines], hide_index=True, use_container_width=True)
    st.metric('Total', money(sum(x['subtotal_centavos'] for x in lines)))


def navigate(label, destination):
    def change_page():
        st.session_state['page'] = destination
    st.button(label, on_click=change_page)
