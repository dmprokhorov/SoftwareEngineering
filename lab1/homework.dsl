workspace {
    !identifiers hierarchical
    model {
        admin = Person "Администратор" "Управляет данными с сервисов"
        user = Person "Пользователь" "Управляет своими доходами и расходами"

        database = softwareSystem "База данных" {
            description "Хранит данные о пользователях, их доходах и расходах."
        }

        API = softwareSystem "API Gateway" {
            description "Обрабатывает запросы от клиентов и админов"
        }

        budgeting_site = softwareSystem "Сайт бюджетирования" {
            description "Система для управления пользователями, доходами и расходами"

            user_service = container "Пользовательский сервис" {
                description "Управляет пользователями."
                technology "Python"
            }

            income_service = container "Сервис доходов" {
                description "Управляет планируемыми доходами"
                technology "Python"
            }

            consumption_service = container "Сервис расходов" {
                description "Управляет планируемыми расходами"
                technology "Python"
            }

            budget_service = container "Сервис бюджета" {
                description "Управляет динамикой бюджета."
                technology "Python"
            }

            API -> user_service "Передача данных о пользователе"
            API -> income_service "Передача данных о доходах"
            API -> consumption_service "Передача данных о расходах"
            API -> budget_service "Передача данных о временном периоде, в течение которого нужно будет посчитать динамику бюджета"
            user_service -> database "Сохранение данных о пользователе в таблице с пользователями"
            income_service -> database "Сохранение данных о доходах в таблице с операциями пользователей"
            consumption_service -> database "Сохранение данных о расходах в таблице с операциями пользователей"
            budget_service -> database "Получение данных для расчета динамики бюджета в таблице с операциями пользователей"
        }

        user -> API "Запрос на управление доходами и расходами" "HTTP"
        admin -> API "Запрос на создание пользователя"
        API -> budgeting_site "Обрабатывает запросы"
    }

    views {
        systemContext budgeting_site "context" {
            include *
            autoLayout
        }

        container budgeting_site "c2" {
            include *
            autoLayout
        }

        dynamic budgeting_site "Add_User" "Добавление пользователя" {
            autolayout lr
            description "Сценарий добавления нового пользователя"
            admin -> API "Запрос на создание нового пользоваеля"
            API -> budgeting_site.user_service "Передача данных о новом пользователе"
            budgeting_site.user_service -> database "Сохранение данных о новом пользователе"
        }

        dynamic budgeting_site "Find_User_By_Login" "Поиск пользователя по логину" {
            autolayout lr
            description "Сценарий поиска пользователя по логину"
            admin -> API "Запрос на поиск пользователя по логину"
            API -> budgeting_site.user_service "Передача логина пользователя"
            budgeting_site.user_service -> database "Поиск пользователя с заданным логином в базе данных"
        }

        dynamic budgeting_site "Find_User_By_Name_And_Surname" "Поиск пользователя по имени и фамилии" {
            autolayout lr
            description "Сценарий поиска пользователя по имени и фамилии"
            admin -> API "Запрос на поиск пользователя по имени и фамилии"
            API -> budgeting_site.user_service "Передача имени и фамилии пользователя"
            budgeting_site.user_service -> database "Поиск пользователя с заданными именем и фамилией в базе данных"
        }

        dynamic budgeting_site "Create_Planned_Income" "Создание планируемого дохода" {
            autolayout lr
            description "Сценарий создания планируемого дохода"
            user -> API "Запрос на создание планируемого дохода"
            API -> budgeting_site.income_service "Передача планиремого дохода"
            budgeting_site.income_service -> database "Сохранение планируемго дохода в базе данных"
        }

        dynamic budgeting_site "Get_List_Of_Planned_Incomes" "Получение перечня планируемых доходов" {
            autolayout lr
            description "Сценарий получения перечня планируемых доходов"
            user -> API "Запрос на получение перечня планируемых доходов"
            API -> budgeting_site.income_service "Передача запроса на получение планируемых доходов"
            budgeting_site.income_service -> database "Поиск всех планируемых доходов в базе данных"
        }

        dynamic budgeting_site "Create_Planned_Consumption" "Создание планируемого расхода" {
            autolayout lr
            description "Сценарий создания планируемого расхода"
            user -> API "Запрос на создание планируемого расхода"
            API -> budgeting_site.income_service "Передача планируемого расхода"
            budgeting_site.income_service -> database "Сохранение планируемго расхода в базе данных"
        }

        dynamic budgeting_site "Get_List_Of_Planned_Consumptions" "Получение перечня планируемых расходов" {
            autolayout lr
            description "Сценарий получения перечня планируемых расходов"
            user -> API "Запрос на получение перечня планируемых расходов"
            API -> budgeting_site.consumption_service "Передача запроса на получение планируемых расходов"
            budgeting_site.consumption_service -> database "Поиск всех планируемых расходов в базе данных"
        }

        dynamic budgeting_site "Get_Budget_Dynamics_For_Period" "Получение динамики бюджета за период" {
            autolayout lr
            description "Сценарий получения динамики бюджета за период"
            user -> API "Запрос на получение динамики бюджета за период"
            API -> budgeting_site.budget_service "Передача конкретного периода в сервис бюджета"
            budgeting_site.budget_service -> database "Подсчёт бюджета за полученный период"
        }
    }
}