# ---------- Handlers ----------
@bot.message_handler(func=lambda m: m.text == "✅ Подписаться")
def handle_subscribe(message):
    uid = message.from_user.id

    # Если уже подписан — показать клавиатуру на его языке
    if is_subscribed(uid):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT language FROM subscribers WHERE user_id = ?", (uid,))
        row = cur.fetchone()
        conn.close()
        user_lang = row[0] if row and row[0] else "🇷🇺 Русский"
        _, kb_after = get_keyboards(user_lang)
        bot.send_message(uid, "Вы уже подписаны ✅", reply_markup=kb_after)
        return

    # Добавляем пользователя в базу (по умолчанию без согласия на рекламу)
    add_subscriber(uid)

    # Сначала показать выбор языка
    kb_languages = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb_languages.add("🇷🇺 Русский", "🇬🇧 Английский")
    kb_languages.add("🇵🇱 Польский", "🇪🇸 Испанский")
    kb_languages.add("🇩🇪 Немецкий", "🇫🇷 Французский")
    kb_languages.add("🇰🇿 Казахский", "🇺🇦 Украинский")
    bot.send_message(uid, "Выберите язык:", reply_markup=kb_languages)


@bot.message_handler(func=lambda m: m.text in [
    "🇷🇺 Русский","🇬🇧 Английский","🇵🇱 Польский","🇪🇸 Испанский",
    "🇩🇪 Немецкий","🇫🇷 Французский","🇰🇿 Казахский","🇺🇦 Украинский"
])
def handle_language(message):
    uid = message.from_user.id
    lang = message.text
    set_language(uid, lang)

    greetings_map = {
       "🇷🇺 Русский": (
        "🇷🇺 Вы выбрали русский язык!\n\n"
        "📦 Отправьте мне ссылку на товар — я буду отслеживать его цену и сообщу, когда она упадёт 💰\n"
        "🕵️ Также я проверю этот товар на других сайтах, чтобы найти где дешевле!\n\n"
        "Поддерживаемые сайты:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Когда найду дешевле или цена упадёт — сразу уведомлю вас 📲"
    ),
    "🇬🇧 Английский": (
        "🇬🇧 You selected English!\n\n"
        "📦 Send me a product link — I’ll track its price and notify you when it drops 💰\n"
        "🕵️ I’ll also check this product on other sites to find where it’s cheaper!\n\n"
        "Supported sites:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "When I find a lower price or a drop — I’ll let you know 📲"
    ),
    "🇵🇱 Польский": (
        "🇵🇱 Wybrałeś język polski!\n\n"
        "📦 Wyślij mi link do produktu — będę śledzić jego cenę i dam znać, gdy spadnie 💰\n"
        "🕵️ Sprawdzę też ten produkt na innych stronach, aby znaleźć tańszą ofertę!\n\n"
        "Obsługiwane strony:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Gdy znajdę niższą cenę lub spadek — natychmiast Cię powiadomię 📲"
    ),
    "🇪🇸 Испанский": (
        "🇪🇸 ¡Has seleccionado Español!\n\n"
        "📦 Envíame un enlace de producto — seguiré su precio y te avisaré cuando baje 💰\n"
        "🕵️ También comprobaré este producto en otros sitios para ver dónde es más barato.\n\n"
        "Sitios compatibles:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Cuando encuentre un precio más bajo o una bajada — te lo notificaré 📲"
    ),
    "🇩🇪 Немецкий": (
        "🇩🇪 Du hast Deutsch gewählt!\n\n"
        "📦 Sende mir den Produktlink — ich verfolge den Preis und informiere dich, wenn er fällt 💰\n"
        "🕵️ Außerdem überprüfe ich das Produkt auf anderen Websites, um den günstigsten Preis zu finden!\n\n"
        "Unterstützte Seiten:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Wenn ich einen besseren Preis finde oder der Preis sinkt — bekommst du sofort eine Benachrichtigung 📲"
    ),
    "🇫🇷 Французский": (
        "🇫🇷 Vous avez choisi Français !\n\n"
        "📦 Envoyez-moi un lien vers un produit — je suivrai son prix et vous informerai dès qu’il baisse 💰\n"
        "🕵️ Je vérifierai aussi ce produit sur d’autres sites pour voir où il est moins cher !\n\n"
        "Sites pris en charge :\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Dès que je trouve un meilleur prix ou une baisse — je vous le dirai 📲"
    ),
    "🇰🇿 Казахский": (
        "🇰🇿 Сіз қазақ тілін таңдадыңыз!\n\n"
        "📦 Маған тауардың сілтемесін жіберіңіз — мен оның бағасын бақылаймын және арзандағанда хабарлаймын 💰\n"
        "🕵️ Сондай-ақ мен бұл тауарды басқа сайттардан қарап, арзанырақ нұсқасын табуға тырысамын!\n\n"
        "Қолдау көрсетілетін сайттар:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Баға түссе немесе арзанырақ табылса — бірден хабарлаймын 📲"
    ),
    "🇺🇦 Украинский": (
        "🇺🇦 Ви обрали українську мову!\n\n"
        "📦 Надішліть мені посилання на товар — я відстежуватиму його ціну та повідомлю, коли вона знизиться 💰\n"
        "🕵️ Також я перевірю цей товар на інших сайтах, щоб знайти, де він дешевше!\n\n"
        "Підтримувані сайти:\n"
        "• Allegro\n"
        "• Temu\n"
        "• AliExpress\n"
        "• Banggood\n"
        "• Alibaba\n\n"
        "Коли знайду нижчу ціну або зниження — одразу повідомлю вас 📲"
    ),
    }

    # Клавиатура после выбора языка — всегда подписка/отписка
    _, kb_after = get_keyboards(lang)
    bot.send_message(uid, greetings_map.get(lang, "Язык сохранён."), reply_markup=kb_after)

    # Inline кнопки для согласия на маркетинг
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Да, хочу рекламные предложения", callback_data=f"marketing_yes:{uid}"),
        types.InlineKeyboardButton("❌ Нет, только уведомления", callback_data=f"marketing_no:{uid}")
    )
    bot.send_message(uid, "Хотите получать рекламные предложения и партнерские ссылки? (можно изменить в любой момент)", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "❌ Отписаться")
def handle_unsubscribe(message):
    uid = message.from_user.id
    remove_subscriber(uid)
    kb_before, _ = get_keyboards("🇷🇺 Русский")  # по умолчанию русская кнопка
    bot.send_message(uid, "Вы отписались 🔕", reply_markup=kb_before)
