#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QJsonDocument>
#include <QTcpSocket>


QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();
    void parse();

public slots:
    void slotReadyRead();
    void choosePage(int);
    void chooseDay(int);
    void login();
    void connected();
    void connectToServer();

protected:
    virtual void timerEvent(QTimerEvent *event);

private:
    Ui::MainWindow *ui;

    QString getSheduleFromServer();
    void showShedule(QString);

    void parseResultlogin(QJsonDocument);
    void parseResultGetShedule(QJsonDocument);

    QMap<QString, QJsonDocument> requests;

    QTcpSocket* socket;
    QByteArray Data;
    quint16 nextBlockSize;

    void sendToServer(QByteArray);
};
#endif // MAINWINDOW_H
