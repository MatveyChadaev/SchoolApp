#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QDebug>
#include <QJsonObject>
#include <QTimer>
#include <QFile>
#include <QUrl>
#include "lesson.h"
#include <QScrollArea>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    socket = new QTcpSocket(this);
    connect(socket,       &QTcpSocket::readyRead,    this,   &MainWindow::slotReadyRead);
    connect(socket,       &QTcpSocket::connected,    this,   &MainWindow::connected);
    connect(socket,       &QTcpSocket::disconnected, socket, &QTcpSocket::deleteLater);
    connect(socket,       &QTcpSocket::disconnected, this,   &MainWindow::connectToServer);
    connect(ui->pb_login, &QPushButton::clicked,     this,   &MainWindow::login);
    nextBlockSize = 0;

    startTimer(1000);

    connect(ui->bg_pages_buttons,   SIGNAL(buttonClicked(int)), this, SLOT(choosePage(int)));
    connect(ui->bg_shedule_buttons, SIGNAL(buttonClicked(int)), this, SLOT(chooseDay(int)));

    ui->stackedWidget_2->setCurrentIndex(2);

    socket->connectToHost("127.0.0.1", 2323);

    QFile file(QUrl("../../settings/userdata.json").path());

    if(!file.open(QIODevice::ReadOnly)) {
        qDebug() << "open error1";
        return;
    }

    QJsonDocument json = QJsonDocument::fromJson(file.readAll());

    file.close();

    if (json["is_login"].toBool()) {
        ui->stackedWidget_4->setCurrentIndex(1);
        ui->pushButton->setEnabled(true);
        ui->pushButton_2->setEnabled(true);

        QFile file2(QUrl("../../settings/shedule.txt").path());

        if(!file2.open(QIODevice::ReadOnly)) {
            qDebug() << "open error1";
            return;
        }

        showShedule(file2.readAll());
        file2.close();
    }
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::slotReadyRead()
{
    QDataStream in(socket);
    in.setVersion(QDataStream::Qt_5_15);

    if (in.status() == QDataStream::Ok) {
        // QString str;
        // in >> str;
        // qDebug() << str;

        while(true) {
            if (nextBlockSize == 0) {
                if (socket->bytesAvailable() < 2) {
                    break;
                }
                in >> nextBlockSize;
            }

            if (socket->bytesAvailable() < nextBlockSize) {
                break;
            }

            QByteArray msg;
            msg.resize(nextBlockSize);
            socket->read(msg.data(), nextBlockSize);
            nextBlockSize = 0;

            QJsonParseError parseError;
            auto request = QJsonDocument::fromJson(msg, &parseError);
            qDebug() << parseError.errorString();
            qDebug() << request;

            switch (requests[request["cookie"].toString()]["type"].toInt()) {
            case 0:
                parseResultlogin(request);
                break;
            case 1:
                parseResultGetShedule(request);
                break;
            default:
                break;
            }
        }
    }
    else {
        qDebug() << "read error";
    }
}

void MainWindow::parseResultlogin(QJsonDocument response) {
    QUrl url = QUrl("../../settings/userdata.json");
    QFile file(url.path());
    if(!file.open(QIODevice::WriteOnly)) {
        qDebug() << "1.open error";
        qDebug() << file.errorString() << url.path();
        return;
    }
    auto output = response.object();

    qDebug() << "1";
    requests.remove(output["cookie"].toString());
    qDebug() << "2";
    output.remove("cookie");

    file.write(QJsonDocument(output).toJson());
    file.close();
    qDebug() << "3";
    if (output["is_login"].toBool()) {
        ui->stackedWidget_4->setCurrentIndex(1);
        ui->pushButton->setEnabled(true);
        ui->pushButton_2->setEnabled(true);
        getSheduleFromServer();
    }
}

void MainWindow::parseResultGetShedule(QJsonDocument response)
{
    QFile file(QUrl("../../settings/shedule.txt").path());
    if(!file.open(QIODevice::WriteOnly)) {
        qDebug() << "1.open error";
        qDebug() << file.errorString();
        return;
    }

    auto json = response.object();
    qDebug() << '1';
    requests.remove(json["cookie"].toString());
    qDebug() << "111";
    file.write(json["shedule"].toString().toStdString().c_str());
    file.close();

    showShedule(json["shedule"].toString());
}

void MainWindow::choosePage(int n)
{
    ui->stackedWidget_2->setCurrentIndex(-n-2);
    qDebug() << ui->stackedWidget_2->currentIndex();
}

void MainWindow::chooseDay(int n)
{
    ui->stackedWidget_3->setCurrentIndex(-n-2);
    qDebug() << ui->stackedWidget_3->currentIndex();
}

void MainWindow::login()
{
    QJsonObject request;
    request["type"]                        = 0;
    request["cookie"]                      = QUuid::createUuid().toString();
    request["login"]                       = ui->le_login->text();
    request["password"]                    = ui->le_password->text();
    requests[request["cookie"].toString()] = QJsonDocument(request);

}

void MainWindow::connected()
{
    ui->stackedWidget->setCurrentIndex(1);
}

void MainWindow::connectToServer()
{
    socket->connectToHost("127.0.0.1", 2323);
    if (socket->state() != QTcpSocket::ConnectedState && socket->state() != QTcpSocket::ConnectingState) {
        QTimer::singleShot(100, this, &MainWindow::connectToServer);
    }
}

void MainWindow::timerEvent(QTimerEvent *event)
{
    Q_UNUSED(event)

    if (socket->state() == QTcpSocket::ConnectedState) {
        for (auto request : requests.values()) {
            sendToServer(QJsonDocument(request).toJson());
            qDebug() << "отправка...";
        }
    }

    // updateLogInStatus();
}

QString MainWindow::getSheduleFromServer() {
    qDebug() << "getSheduleFromServer start";
    QFile file(QUrl("../../settings/shedule.txt").path());
    if(!file.open(QIODevice::ReadOnly)) {
        qDebug() << "open error...";
        return "";
    }

    qDebug() << 1;
    QJsonObject request;
    request["type"]                        = 1;
    request["cookie"]                      = QUuid::createUuid().toString();
    request["Class"]                       = QJsonDocument::fromJson(file.readAll()).object()["Class"].toString();
    requests[request["cookie"].toString()] = QJsonDocument(request);

    file.close();

    qDebug() << "getSheduleFromServer stop";

    return request["cookie"].toString();
}

void MainWindow::showShedule(QString shedule)
{
    QVector<QVector<QString>> result;
    QVector<QString> v;

    QString cur_s = "";

    bool b = false;

    for (int i = 0; i < shedule.length(); i++) {
        if (shedule[i] == '"') {
            if (b) {
                v.push_back(cur_s);
                cur_s = "";
            }
            b = !b;
        }
        else if (shedule[i] == "\n" && !b) {
            result.push_back(v);
            v.clear();
        }
        else if (b) {
            cur_s += shedule[i];
        }
    }

    for (auto i : result) {
        for (int j = 0; j < i.length(); j += 3) {
            auto day = static_cast<QScrollArea*>(ui->stackedWidget_3->children()[j]->children()[0]->children()[0]);
            day->layout()->addWidget(new Lesson(day, i[j], i[j+1], i[j+2]));
        }
    }
}

void MainWindow::sendToServer(QByteArray str)
{
    Data.clear();

    QDataStream out(&Data, QIODevice::WriteOnly);
    // out.setVersion(QDataStream::Qt_5_15);
    quint16 size = str.size();
    out << size;// << str;

    qDebug() << size << ":" << Data;
    socket->write(Data);
    socket->write(str);
}
